"""
Device state and haptic callback utilities for Phantom Omni experiments.
"""
from dataclasses import dataclass, field
from pyOpenHaptics.hd_callback import hd_callback
import pyOpenHaptics.hd as hd

@dataclass
class DeviceState:
    button: bool = False
    position: list = field(default_factory=list)  # [x, y, z]
    force: list = field(default_factory=list)     # [Fx, Fy, Fz]

device_state = DeviceState()

@hd_callback
def state_callback():
    global device_state
    transform = hd.get_transform()
    device_state.position = [transform[3][0], transform[3][1], transform[3][2]]
    device_state.button = (hd.get_buttons() == 1)
    hd.set_force(device_state.force)
