#!/usr/bin/env python
"""
Timed sequence tracker for haptic guidance experiments.
Runs the game for a specified duration and logs distance metrics.
"""

import pygame
from pyOpenHaptics.hd_device import HapticDevice
import pyOpenHaptics.hd as hd
import time
import math
import json
from dataclasses import dataclass, field
from pyOpenHaptics.hd_callback import hd_callback
from linedemo import PhysicsEngine, Renderer, device_state, state_callback

# --- Experiment State ---
@dataclass
class ExperimentData:
    """Stores experiment metrics."""
    start_time: float = 0
    end_time: float = 0
    duration: float = 0  # seconds
    fps: float = 60
    ticks: list = field(default_factory=list)  # List of tick data
    
    def to_json(self):
        """Convert experiment data to JSON-serializable dictionary."""
        return {
            "metadata": {
                "total_duration_seconds": self.duration,
                "target_fps": self.fps,
                "total_ticks": len(self.ticks),
                "average_tick_rate": len(self.ticks) / self.duration if self.duration > 0 else 0
            },
            "ticks": self.ticks
        }

class SequenceTracker:
    """Manages timed sequences and distance tracking for experiments."""
    
    def __init__(self, duration=30, fps=60, k_drag=0.08, k_z=0.15):
        """
        Initialize the sequence tracker.
        
        Args:
            duration: Duration of the experiment in seconds (default: 30)
            fps: Target frames per second (default: 60)
            k_drag: Stiffness for XY plane guidance
            k_z: Stiffness for Z-axis centering
        """
        self.duration = duration
        self.fps = fps
        self.k_drag = k_drag
        self.k_z = k_z
        self.experiment_data = ExperimentData(fps=fps)
        self.tick_counter = 0
    
    def calculate_distance(self, target_x_mm, target_y_mm, dev_x, dev_y):
        """Calculate Euclidean distance between target and cursor in mm."""
        dx = target_x_mm - dev_x
        dy = target_y_mm - dev_y
        return math.sqrt(dx**2 + dy**2)
    
    def run_experiment(self):
        """Run the timed sequence experiment."""
        pygame.init()
        width, height = 800, 600
        surface = pygame.display.set_mode((width, height))
        pygame.display.set_caption(f"Haptic Experiment - {self.duration}s")
        
        clock = pygame.time.Clock()

        print(f"Initializing Haptic Device for {self.duration}s experiment...")
        device = HapticDevice(device_name="Default Device", callback=state_callback)
        time.sleep(0.2)
        
        # Initialize physics and renderer
        physics_engine = PhysicsEngine(k_drag=self.k_drag, k_z=self.k_z)
        renderer = Renderer(width, height)
        
        self.experiment_data.start_time = time.time()
        run = True
        
        while run:
            clock.tick(self.fps)
            elapsed = time.time() - self.experiment_data.start_time
            
            # Check if duration exceeded
            if elapsed >= self.duration:
                run = False
                break
            
            # Handle Pygame Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        run = False

            # Get latest haptic data
            if not device_state.position:
                continue
                
            dev_x, dev_y = device_state.position[0], device_state.position[1]
            
            # Get mouse position
            mouse_x_screen, mouse_y_screen = pygame.mouse.get_pos()
            
            # --- PHYSICS UPDATE ---
            target_x_mm, target_y_mm = physics_engine.update(
                device_state.position, mouse_x_screen, mouse_y_screen, width, height
            )

            # --- TRACK DISTANCE ---
            distance = self.calculate_distance(target_x_mm, target_y_mm, dev_x, dev_y)
            tick_data = {
                "tick": self.tick_counter,
                "elapsed_time": elapsed,
                "device_x": dev_x,
                "device_y": dev_y,
                "target_x": target_x_mm,
                "target_y": target_y_mm,
                "distance_mm": distance,
                "button_pressed": device_state.button
            }
            self.experiment_data.ticks.append(tick_data)
            self.tick_counter += 1

            # --- DRAWING ---
            renderer.render(
                surface, device_state, dev_x, dev_y, 
                mouse_x_screen, mouse_y_screen, target_x_mm, target_y_mm
            )
            
            # Draw elapsed time
            time_text = renderer.font_large.render(
                f"Time: {elapsed:.1f}s / {self.duration}s", 
                True, (200, 200, 200)
            )
            surface.blit(time_text, (width - 350, height - 40))
            pygame.display.flip()

        self.experiment_data.end_time = time.time()
        self.experiment_data.duration = self.experiment_data.end_time - self.experiment_data.start_time
        
        device.close()
        pygame.quit()
        
        print(f"Experiment completed in {self.experiment_data.duration:.2f}s")
        print(f"Total ticks recorded: {len(self.experiment_data.ticks)}")
        
        return self.experiment_data
    
    def save_to_json(self, filepath):
        """Save experiment data to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.experiment_data.to_json(), f, indent=2)
        print(f"Experiment data saved to {filepath}")


def run_timed_experiment(duration=30, k_drag=0.08, k_z=0.15, output_file="experiment_data.json"):
    """
    Convenience function to run a complete experiment and save results.
    
    Args:
        duration: Duration of the experiment in seconds
        k_drag: Stiffness for XY plane guidance
        k_z: Stiffness for Z-axis centering
        output_file: Path to save the JSON output
    """
    tracker = SequenceTracker(duration=duration, k_drag=k_drag, k_z=k_z)
    tracker.run_experiment()
    tracker.save_to_json(output_file)
    return tracker.experiment_data


if __name__ == "__main__":
    # Run a 30-second experiment
    run_timed_experiment(duration=30, k_drag=0.05, k_z=0.15, output_file="experiment_data.json")
