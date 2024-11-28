from manimlib import *
from pyglet.window import key
from pyperclip import copy

class Animation(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()

        self.add(axes)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == key.C and modifiers == key.MOD_SHIFT:
            string = "reorient("
            string += f"{self.frame.get_theta():.2}" + ", "
            string += f"{self.frame.get_phi():.2}" + ", "
            string += f"{self.frame.get_gamma():.2}" + ", "
            string += f"{tuple(map(lambda x: float(f"{x:.2}"), tuple(self.frame.get_center())))}, "
            string += f"{self.frame.get_height():.2}" + ")"

            copy(string)
