"""
Experiment data structure and logging utilities.
"""
from dataclasses import dataclass, field
import json

@dataclass
class ExperimentData:
    start_time: float = 0
    end_time: float = 0
    duration: float = 0
    fps: float = 60
    ticks: list = field(default_factory=list)
    participant_id: str = ""
    haptic_enabled: bool = True
    def to_json(self):
        return {
            "metadata": {
                "participant_id": self.participant_id,
                "haptic_enabled": self.haptic_enabled,
                "total_duration_seconds": self.duration,
                "target_fps": self.fps,
                "total_ticks": len(self.ticks),
                "average_tick_rate": len(self.ticks) / self.duration if self.duration > 0 else 0
            },
            "ticks": self.ticks
        }
    def save(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.to_json(), f, indent=2)
