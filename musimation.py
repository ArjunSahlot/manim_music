from manimlib import *
from manimlib.utils.color import random_bright_color
from pyglet.window import key
from pyperclip import copy
import mido

def get_path_between_pads(start, end, max_height=None, resolution=None):
    start = np.array(start)
    end = np.array(end)
    end -= start

    full_dist = np.linalg.norm(end)
    resolution = max(2, int(resolution * 50))

    # if full dist is close to 0, then return a straight line
    if full_dist.round(3) == 0:
        return np.vstack((start, end))

    dists = np.linspace(0, full_dist, resolution)
    heights = np.array([])
    midp = dists[-1] / 2
    for d in dists:
        height = max_height
        if max_height is None:
            # https://www.desmos.com/calculator/vrkbcdyplu
            height = np.abs((5/(1+np.power(np.e, -0.2*full_dist))) - (5/2))
        heights = np.append(heights, height-(height/np.square(midp))*np.square(d-midp))

    coords = np.dstack((np.linspace(0, end[0], resolution), np.linspace(0, end[1], resolution), heights)).reshape(resolution, 3)
    offset = coords + np.vstack((start,) * resolution)
    return offset


def get_notes(file_path):
    mid = mido.MidiFile(file_path)
    notes = []
    max_simul_notes = 0
    simul_notes = 0
    for track in mid.tracks:
        tempo = 500000
        time = 0
        start_keys = [None] * 88
        for msg in track:
            time += msg.time/mid.ticks_per_beat * tempo/1000000
            if msg.is_meta:
                if msg.type == "set_tempo":
                    tempo = msg.tempo
            else:
                if msg.type in ("note_on", "note_off"):
                    if not msg.velocity or msg.type == "note_off":
                        simul_notes -= 1
                        notes.append(
                            {"note": msg.note - 21, "start": start_keys[msg.note - 21], "end": time})
                    else:
                        simul_notes += 1
                        start_keys[msg.note - 21] = time

            max_simul_notes = max(max_simul_notes, simul_notes)
    
    relevant_notes = []
    for note in notes:
        if note["start"] is not None:
            relevant_notes.append([note["note"], note["start"]])

    relevant_notes = np.array(relevant_notes)
    relevant_notes[:, 0] -= np.average(relevant_notes[:, 0])
    relevant_notes[:, 1] *= 16

    return relevant_notes, max_simul_notes


def create_pads(self, axes, notes, animate=True):
    init_pos = axes.c2p(*np.average(notes, axis=0), 10)
    # init_pos = axes.c2p(0, 0, 0.01)
    pads = [Square3D(1, color=BLUE).move_to(init_pos) for _ in range(len(notes))]
    self.add(*pads)
    if animate:
        self.play(*(pad.animate.move_to(axes.c2p(notes[i][0], notes[i][1], 0.01)) for i, pad in enumerate(pads)))

    return pads


def calculate_paths(axes, notes, agents=1):
    paths = {}
    for i in range(agents):
        ball = Sphere(radius=0.2, color=random_bright_color())
        init_pos = axes.c2p(i-agents/2, 0, 0.01)
        paths[ball] = [init_pos[:2]]

    for i in range(len(notes)):
        # which agent is the best to take this note?
        agents = list(paths.keys())
        
        def score(agent):
            prev_loc = paths[agent][-1]
            proximity = np.abs(prev_loc - notes[i])
            x_proximity = proximity[0]
            y_proximity = proximity[1]

            return x_proximity - y_proximity

        best = sorted(agents, key=score)[0]
        paths[best].append(notes[i])

    for ball, locs in paths.items():
        if len(locs) == 0:
            continue
        start_path = np.array([list(axes.c2p(locs[0][0], locs[0][1], 0.01))])
        ball.move_to(start_path[0])
        for i in range(1, len(locs)):
            start_path = np.concatenate((
                start_path,
                get_path_between_pads(axes.c2p(locs[i-1][0], locs[i-1][1], 0.01), axes.c2p(locs[i][0], locs[i][1], 0.01), resolution=locs[i][1]-locs[i-1][1])
            ))
        
        start_path = np.concatenate((
            start_path,
            get_path_between_pads(axes.c2p(locs[-1][0], locs[-1][1], 0.01), axes.c2p(notes[-1][0], notes[-1][1], 0.01), resolution=notes[-1][1]-locs[-1][1])
        ))
        start_path[:, 2] += ball.get_width()/2
        paths[ball] = VMobject()
        paths[ball].set_points_as_corners(start_path)

    return paths


class Musimation(ThreeDScene):
    def construct(self):
        width = 20
        length = 50
        axes = ThreeDAxes(
            x_range=[-width/2, width/2, 1],
            y_range=[-5, length, 1],
        )

        # self.frame.reorient(4.1e+01, 6.8e+01, 4.8e-14, (12.0, -14.3, 4.1), 3.1e+01)
        self.frame.reorient(4.1e+01, 6.8e+01, 5.1e-14, (4.2, -28.0, 2.0), 3.6e+01)

        # notes = [(freq, time)]
        notes, agents = get_notes(Path.home() / "Downloads" / "piano.mid")

        min_note = np.min(notes[:, 1])
        max_note = np.max(notes[:, 1])

        pads: list[Square3D] = create_pads(self, axes, notes)

        # {Ball: VMobject}
        paths = calculate_paths(axes, notes, agents=agents)

        balls = list(paths.keys())
        path_points = list(paths.values())

        self.play(*(ShowCreation(path) for path in path_points))
        self.play(
            *(FadeOut(path) for path in path_points),
            *(FadeIn(ball) for ball in balls)
        )

        self.add(*[
            TracingTail(
                ball,
                time_traced=3,
                stroke_width=(0, 10)
            ).match_color(ball) for ball in balls
        ])

        self.play(
            *(
                MoveAlongPath(ball, path, rate_func=linear)
                for ball, path in zip(balls, path_points)
            ),
            # self.frame.animate.reorient(3.3e+01, 5.7e+01, -3.2e-15, (11.0, 96.0, 8.6), 3e+01),
            self.frame.animate.set_y(max_note-(min_note-self.frame.get_y())+15),
            run_time=max_note/16,
            rate_func=linear
        )

        self.play(*(FadeOut(ball) for ball in balls))


    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == key.C and modifiers == key.MOD_SHIFT:
            string = "reorient("
            string += f"{(self.frame.get_theta()/DEGREES):.2}" + ", "
            string += f"{(self.frame.get_phi()/DEGREES):.2}" + ", "
            string += f"{(self.frame.get_gamma()/DEGREES):.2}" + ", "
            string += f"{tuple(map(lambda x: float(f"{x:.2}"), tuple(self.frame.get_center())))}, "
            string += f"{self.frame.get_height():.2}" + ")"

            copy(string)
