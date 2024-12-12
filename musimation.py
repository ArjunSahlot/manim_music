from manimlib import *
from manimlib.utils.color import random_bright_color
from pyglet.window import key
from pyperclip import copy
from pathlib import Path
import mido


def get_path_between_pads(start, end, max_height=None, time=1):
    start = np.array(start)
    end = np.array(end)
    end -= start

    full_dist = np.linalg.norm(end)
    resolution = max(2, int(PATH_RESOLUTION * time/RUN_TIME))

    # if full dist is close to 0, then return a straight line
    if full_dist.round(3) == 0:
        return np.vstack((start, start))

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


def create_pads(self, axes, animate=True):
    init_pos = axes.c2p(0, 0, 0.01)
    pads = [Square3D(1, color=BLUE).move_to(init_pos) for _ in range(NUM_NOTES)]
    self.add(*pads)
    if animate:
        self.play(
            *(pad.animate.move_to(axes.c2p(NOTES[i][0], NOTES[i][1]*Y_AXIS_SCALE, 0.01)) for i, pad in enumerate(pads)),
            run_time=2
        )

    return pads


def calculate_paths(axes, pads):
    pad_locs = np.array([np.array(list(axes.p2c(pad.get_center()))) for pad in pads])
    paths = {}
    for i in range(AGENTS):
        ball = Sphere(radius=0.2, color=random_bright_color())
        init_pos = (i-AGENTS/2, -12, 0.01)
        ball.move_to(axes.c2p(*init_pos))
        paths[ball] = [init_pos]

    for i in range(len(pad_locs)):
        balls = list(paths.keys())

        def score(agent):
            prev_loc = paths[agent][-1]
            proximity = np.abs(prev_loc - pad_locs[i])
            x_proximity = proximity[0]
            y_proximity = proximity[1]

            return x_proximity - y_proximity

        best = sorted(balls, key=score)[0]
        paths[best].append(pad_locs[i])

    for ball, locs in paths.items():
        if len(locs) == 0:
            continue
        start_path = get_path_between_pads(
            axes.c2p(*locs[0]),
            axes.c2p(*locs[1]),
            time=RUNUP_TIME + locs[1][1]/Y_AXIS_SCALE
        )
        for i in range(2, len(locs)):
            start_path = np.concatenate((
                start_path,
                get_path_between_pads(
                    axes.c2p(*locs[i-1]),
                    axes.c2p(*locs[i]),
                    time=(locs[i][1]-locs[i-1][1])/Y_AXIS_SCALE
                )
            ))
        
        start_path = np.concatenate((
            start_path,
            get_path_between_pads(
                axes.c2p(*locs[-1]),
                axes.c2p(*pad_locs[-1]),
                time=(pad_locs[-1][1]-locs[-1][1])/Y_AXIS_SCALE
            )
        ))
        start_path[:, 2] += ball.get_width()/2
        paths[ball] = VMobject()
        paths[ball].set_points_as_corners(start_path)

    return paths


def get_notes():
    mid = mido.MidiFile(MIDI_FILE)
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

    return relevant_notes, max_simul_notes


Y_AXIS_SCALE = 16
RUNUP_TIME = 1
MIDI_FILE = Path.home() / "Downloads" / "piano.mid"
NOTES, AGENTS = get_notes()
# AGENTS = 10  # for 10 fingers on complicated piano music
print(NOTES)
print(AGENTS)
NUM_NOTES = len(NOTES)
MIN_NOTE = np.min(NOTES[:, 1])
MAX_NOTE = np.max(NOTES[:, 1])
NOTES_RANGE = MAX_NOTE - MIN_NOTE
RUN_TIME = MAX_NOTE + RUNUP_TIME
PATH_RESOLUTION = NUM_NOTES * 25


class Musimation(ThreeDScene):
    def construct(self):
        width = 20
        length = 50
        axes = ThreeDAxes(
            x_range=[-width/2, width/2, 1],
            y_range=[-5, length, 1],
        )

        self.frame.reorient(3.4e+01, 7.1e+01, 6.7e-14, (11.0, -29.0, 0.93), 2.6e+01)

        pads: list[Square3D] = create_pads(self, axes)

        # {Ball: VMobject}
        paths = calculate_paths(axes, pads)

        balls = list(paths.keys())
        path_points = list(paths.values())

        self.play(*(FadeIn(ball) for ball in balls))

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
            self.frame.animate.set_y(NOTES_RANGE*Y_AXIS_SCALE+self.frame.get_y()+20),
            run_time=RUN_TIME,
            rate_func=linear
        )

        self.play(
            *(FadeOut(ball) for ball in balls),
            *(FadeOut(pad) for pad in pads),
        )


    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == key.C and modifiers == key.MOD_SHIFT:
            string = "reorient("
            string += f"{(self.frame.get_theta()/DEGREES):.2}" + ", "
            string += f"{(self.frame.get_phi()/DEGREES):.2}" + ", "
            string += f"{(self.frame.get_gamma()/DEGREES):.2}" + ", "
            string += f"{tuple(map(lambda x: float(f"{x:.2}"), tuple(self.frame.get_center())))}, "
            string += f"{self.frame.get_height():.2}" + ")"

            copy(string)
