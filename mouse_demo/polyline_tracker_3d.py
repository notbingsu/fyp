#!/usr/bin/env python
"""
3D Polyline Tracker for haptic guidance experiments.
Creates a 3D path for users to follow with haptic guidance.
Only terminates when BOTH 30 seconds have elapsed AND user reaches the endpoint.
"""

import pygame
from pyOpenHaptics.hd_device import HapticDevice
import pyOpenHaptics.hd as hd
import time
import math
import json
from dataclasses import dataclass, field
from pyOpenHaptics.hd_callback import hd_callback

# --- 1. Shared State ---
@dataclass
class DeviceState:
    button: bool = False
    position: list = field(default_factory=list)  # [x, y, z]
    force: list = field(default_factory=list)     # [Fx, Fy, Fz]

device_state = DeviceState()

# --- 2. Haptic Loop (1000Hz) ---
@hd_callback
def state_callback():
    global device_state
    
    # READ Position
    transform = hd.get_transform()
    current_pos = [transform[3][0], transform[3][1], transform[3][2]]
    device_state.position = current_pos
    
    # READ Button
    buttons = hd.get_buttons()
    is_pressed = (buttons == 1)
    device_state.button = is_pressed

    # APPLY FORCES (only if button pressed for safety)
    if is_pressed:
        hd.set_force(device_state.force)
    else:
        hd.set_force([0, 0, 0])

# --- 3. Experiment Data ---
@dataclass
class ExperimentData:
    """Stores experiment metrics."""
    start_time: float = 0
    end_time: float = 0
    duration: float = 0
    fps: float = 60
    ticks: list = field(default_factory=list)
    
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

# --- 4. 3D Polyline Path ---
class PolylinePath3D:
    """Defines a 3D polyline path with multiple waypoints."""
    
    def __init__(self):
        """Initialize the 3D polyline path with 40 waypoints."""
        # Define waypoints in mm: [x, y, z]
        # Starting from origin, creating a complex 3D path
        self.waypoints = [
            [0, 0, 0],          # 1: Start at origin
            [20, 15, 8],        # 2: Move forward-right-up
            [35, 30, 18],       # 3: Continue pattern
            [45, 45, 30],       # 4: Diagonal ascent
            [50, 60, 40],       # 5: Move up and forward
            [45, 75, 48],       # 6: Continue forward-up
            [30, 85, 52],       # 7: Move left and forward, peak
            [10, 90, 50],       # 8: Continue left, maintain height
            [-10, 88, 45],      # 9: Cross center, drop slightly
            [-30, 82, 38],      # 10: Move further left, descend
            [-45, 72, 30],      # 11: Continue left-back-down
            [-55, 58, 22],      # 12: Deeper left-back
            [-58, 42, 15],      # 13: Continue descent
            [-55, 25, 10],      # 14: Back towards center height
            [-45, 10, 5],       # 15: Approaching start height
            [-30, -5, 0],       # 16: Cross below start Y
            [-15, -15, -5],     # 17: Drop below start
            [0, -22, -10],      # 18: Center X, low point
            [15, -25, -8],      # 19: Start ascending
            [30, -28, -5],      # 20: Move right, rise
            [45, -25, 0],       # 21: Continue right, rise
            [58, -18, 8],       # 22: Right edge, ascending
            [65, -8, 18],       # 23: Peak right
            [68, 5, 28],        # 24: Continue up
            [65, 18, 38],       # 25: Move left, rise
            [58, 30, 46],       # 26: Continue left-forward-up
            [48, 42, 52],       # 27: Approaching peak
            [35, 50, 56],       # 28: Near peak
            [20, 55, 58],       # 29: Peak height
            [5, 58, 56],        # 30: Move left at peak
            [-10, 58, 52],      # 31: Continue left, descend
            [-22, 55, 46],      # 32: Left-back-down
            [-32, 48, 40],      # 33: Continue descent
            [-38, 38, 34],      # 34: Diagonal down
            [-40, 26, 28],      # 35: Continue diagonal
            [-38, 14, 22],      # 36: Approaching end
            [-30, 5, 18],       # 37: Move towards end
            [-18, -2, 14],      # 38: Near endpoint
            [-8, -5, 10],       # 39: Close to end
            [0, -8, 8],         # 40: Endpoint
        ]
        
        self.current_waypoint_index = 0
        self.completion_threshold = 8.0  # mm - distance to consider waypoint reached
        self.endpoint_threshold = 10.0   # mm - distance to consider endpoint reached
    
    def get_current_target(self):
        """Returns the current target waypoint."""
        if self.current_waypoint_index < len(self.waypoints):
            return self.waypoints[self.current_waypoint_index]
        return self.waypoints[-1]  # Return last point if we've finished
    
    def is_at_endpoint(self, position):
        """Check if user is at the final endpoint."""
        endpoint = self.waypoints[-1]
        distance = self.calculate_distance_3d(position, endpoint)
        return distance <= self.endpoint_threshold
    
    def calculate_distance_3d(self, pos1, pos2):
        """Calculate 3D Euclidean distance between two points."""
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        dz = pos2[2] - pos1[2]
        return math.sqrt(dx**2 + dy**2 + dz**2)
    
    def update(self, current_position):
        """
        Update path progress based on current position.
        Returns: (current_target, distance_to_target, progress_ratio)
        """
        target = self.get_current_target()
        distance = self.calculate_distance_3d(current_position, target)
        
        # Check if we've reached the current waypoint
        if distance <= self.completion_threshold and self.current_waypoint_index < len(self.waypoints) - 1:
            self.current_waypoint_index += 1
            target = self.get_current_target()
            distance = self.calculate_distance_3d(current_position, target)
        
        # Calculate overall progress
        progress_ratio = self.current_waypoint_index / (len(self.waypoints) - 1)
        
        return target, distance, progress_ratio

# --- 5. Physics Engine for 3D Guidance ---
class PhysicsEngine3D:
    """Handles physics calculations for 3D haptic guidance along polyline."""
    
    def __init__(self, k_xy=0.06, k_z=0.15):
        """
        Initialize the physics engine.
        
        Args:
            k_xy: Stiffness for XY plane guidance (higher = stronger force)
            k_z: Stiffness for Z-axis guidance (higher = stronger force)
        """
        self.k_xy = k_xy
        self.k_z = k_z
    
    def calculate_guidance_force(self, dev_pos, target_pos):
        """
        Calculates a force that pulls the user towards the target position in 3D.
        Updates the global device_state with the calculated force.
        Uses different stiffness for XY plane vs Z axis.
        """
        x, y, z = dev_pos[0], dev_pos[1], dev_pos[2]
        target_x, target_y, target_z = target_pos[0], target_pos[1], target_pos[2]
        
        # Calculate attractive force towards target with separate XY and Z stiffness
        f_x = self.k_xy * (target_x - x)
        f_y = self.k_xy * (target_y - y)
        f_z = self.k_z * (target_z - z)

        # Update global state
        device_state.force = [f_x, f_y, f_z]
        
        return [f_x, f_y, f_z]

# --- 6. Renderer for 3D Polyline ---
class Renderer3D:
    """Handles all drawing operations for the 3D polyline path."""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.scale = 4.0  # Pixels per mm
        self.center_x = width // 2
        self.center_y = height // 2
        self.font_large = pygame.font.SysFont('Arial', 28, bold=True)
        self.font_medium = pygame.font.SysFont('Arial', 20)
        self.font_small = pygame.font.SysFont('Courier', 16)
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.GRAY = (100, 100, 100)
        self.DARK_GRAY = (50, 50, 50)
        self.RED = (255, 50, 50)      # Current user position
        self.BLUE = (50, 150, 255)    # Current target waypoint
        self.GREEN = (100, 255, 100)  # Completed path
        self.YELLOW = (255, 255, 100) # Remaining path
        self.ORANGE = (255, 165, 0)   # Endpoint
        self.BLACK = (0, 0, 0)
    
    def screen_from_haptic(self, haptic_x, haptic_y):
        """Convert haptic XY coordinates (mm) to screen pixels."""
        screen_x = self.center_x + (haptic_x * self.scale)
        screen_y = self.center_y - (haptic_y * self.scale)  # Invert Y for screen
        return int(screen_x), int(screen_y)
    
    def draw_polyline_path(self, surface, waypoints, current_index):
        """Draw the complete 3D polyline path with color coding."""
        # Draw completed segments in green
        for i in range(current_index):
            if i + 1 < len(waypoints):
                start_screen = self.screen_from_haptic(waypoints[i][0], waypoints[i][1])
                end_screen = self.screen_from_haptic(waypoints[i+1][0], waypoints[i+1][1])
                pygame.draw.line(surface, self.GREEN, start_screen, end_screen, 3)
        
        # Draw remaining segments in yellow
        for i in range(current_index, len(waypoints) - 1):
            start_screen = self.screen_from_haptic(waypoints[i][0], waypoints[i][1])
            end_screen = self.screen_from_haptic(waypoints[i+1][0], waypoints[i+1][1])
            pygame.draw.line(surface, self.YELLOW, start_screen, end_screen, 2)
        
        # Draw waypoint markers
        for i, waypoint in enumerate(waypoints):
            screen_pos = self.screen_from_haptic(waypoint[0], waypoint[1])
            
            if i < current_index:
                # Completed waypoints - small green dots
                pygame.draw.circle(surface, self.GREEN, screen_pos, 4)
            elif i == current_index:
                # Current target - large blue circle
                pygame.draw.circle(surface, self.BLUE, screen_pos, 12)
                pygame.draw.circle(surface, self.WHITE, screen_pos, 12, 2)
            elif i == len(waypoints) - 1:
                # Endpoint - orange star-like marker
                pygame.draw.circle(surface, self.ORANGE, screen_pos, 15)
                pygame.draw.circle(surface, self.WHITE, screen_pos, 15, 2)
                # Draw "END" label
                end_label = self.font_small.render("END", True, self.WHITE)
                surface.blit(end_label, (screen_pos[0] - 15, screen_pos[1] - 30))
            else:
                # Future waypoints - small gray dots
                pygame.draw.circle(surface, self.GRAY, screen_pos, 3)
    
    def draw_user_position(self, surface, dev_x, dev_y):
        """Draw the current user position."""
        screen_x, screen_y = self.screen_from_haptic(dev_x, dev_y)
        pygame.draw.circle(surface, self.RED, (screen_x, screen_y), 10)
        # Draw crosshair
        pygame.draw.line(surface, self.WHITE, (screen_x - 15, screen_y), (screen_x + 15, screen_y), 2)
        pygame.draw.line(surface, self.WHITE, (screen_x, screen_y - 15), (screen_x, screen_y + 15), 2)
    
    def draw_z_depth_indicator(self, surface, target_z, dev_z, all_waypoints):
        """Draw a Z-depth indicator bar showing all waypoints."""
        bar_x = self.width - 80
        bar_y = 100
        bar_width = 50
        bar_height = 400
        z_range = 120  # Total Z range to display (±60mm)
        
        # Draw bar background
        pygame.draw.rect(surface, self.DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(surface, self.WHITE, (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Draw center line (Z=0)
        center_y = bar_y + bar_height // 2
        pygame.draw.line(surface, self.GRAY, (bar_x, center_y), (bar_x + bar_width, center_y), 1)
        
        # Draw all waypoints on Z-axis
        for waypoint in all_waypoints:
            z = waypoint[2]
            z_pos = center_y - int((z / z_range) * bar_height)
            z_pos = max(bar_y, min(bar_y + bar_height, z_pos))
            pygame.draw.circle(surface, self.YELLOW, (bar_x + bar_width // 2, z_pos), 3)
        
        # Draw target Z position (blue)
        target_z_pos = center_y - int((target_z / z_range) * bar_height)
        target_z_pos = max(bar_y, min(bar_y + bar_height, target_z_pos))
        pygame.draw.circle(surface, self.BLUE, (bar_x + bar_width // 2, target_z_pos), 10)
        
        # Draw device Z position (red)
        dev_z_pos = center_y - int((dev_z / z_range) * bar_height)
        dev_z_pos = max(bar_y, min(bar_y + bar_height, dev_z_pos))
        pygame.draw.circle(surface, self.RED, (bar_x + bar_width // 2, dev_z_pos), 8)
        
        # Labels
        z_label = self.font_medium.render("Z-Depth", True, self.WHITE)
        surface.blit(z_label, (bar_x - 15, bar_y - 30))
        
        # Z values
        target_z_text = self.font_small.render(f"{target_z:.1f}", True, self.BLUE)
        surface.blit(target_z_text, (bar_x + bar_width + 5, target_z_pos - 8))
        
        dev_z_text = self.font_small.render(f"{dev_z:.1f}", True, self.RED)
        surface.blit(dev_z_text, (bar_x - 45, dev_z_pos - 8))
    
    def draw_status_panel(self, surface, elapsed, distance, progress, waypoint_index, total_waypoints, at_endpoint):
        """Draw comprehensive status panel."""
        panel_x = 20
        panel_y = 20
        
        # Title
        title = self.font_large.render("3D Polyline Tracker", True, self.WHITE)
        surface.blit(title, (panel_x, panel_y))
        
        # Time elapsed
        time_text = self.font_medium.render(f"Time Elapsed: {elapsed:.1f}s", True, self.WHITE)
        surface.blit(time_text, (panel_x, panel_y + 40))
        
        # Progress
        progress_text = self.font_medium.render(f"Progress: {progress*100:.1f}% ({waypoint_index}/{total_waypoints-1})", True, self.WHITE)
        surface.blit(progress_text, (panel_x, panel_y + 70))
        
        # Distance to target
        distance_color = self.GREEN if distance < 15 else self.WHITE
        distance_text = self.font_medium.render(f"Distance to Target: {distance:.2f} mm", True, distance_color)
        surface.blit(distance_text, (panel_x, panel_y + 100))
        
        # Endpoint status
        if at_endpoint:
            completion_text = self.font_large.render("COMPLETE! Exiting...", True, self.GREEN)
            surface.blit(completion_text, (self.width // 2 - 150, self.height // 2))
        
        # Button status
        if device_state.button:
            status_text = self.font_small.render("Status: ACTIVE (Haptic guidance enabled)", True, self.GREEN)
        else:
            status_text = self.font_small.render("Status: DISABLED (Hold button to enable)", True, self.ORANGE)
        surface.blit(status_text, (panel_x, self.height - 40))
    
    def draw_coordinates(self, surface, target_pos, dev_pos):
        """Draw 3D coordinates."""
        panel_x = 20
        panel_y = self.height - 120
        
        target_text = self.font_small.render(
            f"Target:  X={target_pos[0]:6.1f}  Y={target_pos[1]:6.1f}  Z={target_pos[2]:6.1f}", 
            True, self.BLUE
        )
        cursor_text = self.font_small.render(
            f"Cursor:  X={dev_pos[0]:6.1f}  Y={dev_pos[1]:6.1f}  Z={dev_pos[2]:6.1f}", 
            True, self.RED
        )
        
        surface.blit(target_text, (panel_x, panel_y))
        surface.blit(cursor_text, (panel_x, panel_y + 25))

# --- 7. Main Polyline Tracker ---
class PolylineTracker3D:
    """Main class for running the 3D polyline tracking experiment."""
    
    def __init__(self, fps=60, k_xy=0.06, k_z=0.15):
        """
        Initialize the polyline tracker.
        
        Args:
            fps: Target frames per second
            k_xy: Stiffness for XY plane haptic guidance
            k_z: Stiffness for Z-axis haptic guidance
        """
        self.fps = fps
        self.k_xy = k_xy
        self.k_z = k_z
        self.experiment_data = ExperimentData(fps=fps)
        self.tick_counter = 0
    
    def run_experiment(self):
        """Run the 3D polyline tracking experiment."""
        pygame.init()
        width, height = 1000, 700
        surface = pygame.display.set_mode((width, height))
        pygame.display.set_caption("3D Polyline Tracker - Follow the Path")
        
        clock = pygame.time.Clock()

        print("Initializing Haptic Device for 3D Polyline Tracking...")
        device = HapticDevice(device_name="Default Device", callback=state_callback)
        time.sleep(0.2)
        
        # Initialize components
        path = PolylinePath3D()
        physics_engine = PhysicsEngine3D(k_xy=self.k_xy, k_z=self.k_z)
        renderer = Renderer3D(width, height)
        
        self.experiment_data.start_time = time.time()
        run = True
        
        print(f"\n=== 3D Polyline Tracking Started ===")
        print(f"Total waypoints: {len(path.waypoints)}")
        print(f"Follow the blue target along the yellow path.")
        print(f"The experiment will end when you reach the orange endpoint marker.")
        print(f"Visit all waypoints in sequence to complete the path.")
        print(f"======================================\n")
        
        while run:
            clock.tick(self.fps)
            elapsed = time.time() - self.experiment_data.start_time
            
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
            
            dev_pos = device_state.position
            dev_x, dev_y, dev_z = dev_pos[0], dev_pos[1], dev_pos[2]
            
            # Update path and get current target
            target_pos, distance, progress = path.update(dev_pos)
            target_x, target_y, target_z = target_pos[0], target_pos[1], target_pos[2]
            
            # Check if at endpoint
            at_endpoint = path.is_at_endpoint(dev_pos)
            
            # TERMINATION CONDITION: Endpoint reached (all waypoints visited)
            if at_endpoint:
                print(f"\n=== Experiment Complete! ===")
                print(f"Time elapsed: {elapsed:.2f}s")
                print(f"All waypoints visited: YES")
                print(f"Reached endpoint: YES")
                print(f"===========================\n")
                run = False
                break
            
            # Calculate and apply haptic guidance force
            force = physics_engine.calculate_guidance_force(dev_pos, target_pos)
            
            # Track data
            tick_data = {
                "tick": self.tick_counter,
                "elapsed_time": elapsed,
                "device_x": dev_x,
                "device_y": dev_y,
                "device_z": dev_z,
                "target_x": target_x,
                "target_y": target_y,
                "target_z": target_z,
                "distance_mm": distance,
                "waypoint_index": path.current_waypoint_index,
                "progress_ratio": progress,
                "force_x": force[0],
                "force_y": force[1],
                "force_z": force[2],
                "button_pressed": device_state.button,
                "at_endpoint": at_endpoint
            }
            self.experiment_data.ticks.append(tick_data)
            self.tick_counter += 1

            # RENDERING
            surface.fill(renderer.BLACK)
            
            # Draw path
            renderer.draw_polyline_path(surface, path.waypoints, path.current_waypoint_index)
            
            # Draw user position
            renderer.draw_user_position(surface, dev_x, dev_y)
            
            # Draw Z-depth indicator
            renderer.draw_z_depth_indicator(surface, target_z, dev_z, path.waypoints)
            
            # Draw status panel
            renderer.draw_status_panel(
                surface, elapsed, distance, progress, 
                path.current_waypoint_index, len(path.waypoints),
                at_endpoint
            )
            
            # Draw coordinates
            renderer.draw_coordinates(surface, target_pos, dev_pos)
            
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


def run_polyline_experiment(k_xy=0.06, k_z=0.15, output_file="polyline_experiment_data.json"):
    """
    Convenience function to run the 3D polyline experiment and save results.
    
    Args:
        k_xy: Stiffness for XY plane haptic guidance
        k_z: Stiffness for Z-axis haptic guidance
        output_file: Path to save the JSON output
    """
    tracker = PolylineTracker3D(fps=60, k_xy=k_xy, k_z=k_z)
    tracker.run_experiment()
    tracker.save_to_json(output_file)
    return tracker.experiment_data


if __name__ == "__main__":
    # Run the 3D polyline tracking experiment
    # XY force reduced to 0.06, Z force increased to 0.15 for balanced perception
    run_polyline_experiment(k_xy=0.06, k_z=0.15, output_file="polyline_experiment_data.json")
