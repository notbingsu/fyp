#!/usr/bin/env python
import pygame
from pyOpenHaptics.hd_device import HapticDevice
import pyOpenHaptics.hd as hd
import time
import math
from dataclasses import dataclass, field
from pyOpenHaptics.hd_callback import hd_callback

# --- 1. Shared State ---
@dataclass
class DeviceState:
    button: bool = False
    position: list = field(default_factory=list) # [x, y, z]
    force: list = field(default_factory=list)    # [Fx, Fy, Fz]

device_state = DeviceState()

# --- 2. Haptic Loop (1000Hz) ---
@hd_callback
def state_callback():
    global device_state
    
    # READ Position
    transform = hd.get_transform()
    joints = hd.get_joints()
    
    # Store position (Standard haptic coords: X=Right, Y=Up, Z=Back)
    current_pos = [transform[3][0], transform[3][1], transform[3][2]]
    device_state.position = current_pos
    
    # READ Button (Safety Switch)
    buttons = hd.get_buttons()
    is_pressed = (buttons == 1)
    device_state.button = is_pressed

    # CALCULATE FORCES
    # Only apply force if the button is pressed!
    if is_pressed:
        hd.set_force(device_state.force)
    else:
        # If button released, zero force immediately
        hd.set_force([0, 0, 0])

# --- 3. Physics Engine Class ---
class PhysicsEngine:
    """Handles all physics calculations for haptic guidance."""
    def __init__(self, k_drag=0.08, k_z=0.15):
        """
        Initialize the physics engine.
        
        Args:
            k_drag: Stiffness for XY plane guidance (higher = stronger force)
            k_z: Stiffness for Z-axis centering (higher = stronger force)
        """
        self.k_drag = k_drag
        self.k_z = k_z
    
    def calculate_guidance_force(self, dev_pos, target_x, target_y):
        """
        Calculates a force that pulls the user towards the target position.
        Updates the global device_state with the calculated force.
        """
        x, y, z = dev_pos[0], dev_pos[1], dev_pos[2]
        
        # Drag the user towards the target position (X and Y axes)
        f_x = self.k_drag * (target_x - x)
        f_y = self.k_drag * (target_y - y)
        
        # Keep Z-axis centered
        f_z = self.k_z * (0 - z)

        # Update global state
        device_state.force = [f_x, f_y, f_z]
    
    def update(self, dev_pos, mouse_x_screen, mouse_y_screen, width, height):
        """
        Updates physics based on current device position and mouse location.
        Returns target coordinates in mm.
        """
        scale = 3.0
        center_x, center_y = width // 2, height // 2
        target_x_mm = (mouse_x_screen - center_x) / scale
        target_y_mm = -(mouse_y_screen - center_y) / scale  # Invert Y for haptic coords
        
        self.calculate_guidance_force(dev_pos, target_x_mm, target_y_mm)
        
        return target_x_mm, target_y_mm

# --- 4. Renderer Class ---
class Renderer:
    """Handles all drawing operations."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.scale = 3.0
        self.center_x = width // 2
        self.center_y = height // 2
        self.font_large = pygame.font.SysFont('Arial', 24)
        self.font_small = pygame.font.SysFont('Courier', 16)
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.GRAY = (100, 100, 100)
        self.RED = (255, 50, 50)      # The User
        self.BLUE = (50, 50, 255)     # The Target
        self.GREEN = (100, 255, 100)  # Distance visualization
        self.BLACK = (0, 0, 0)
    
    def screen_from_haptic(self, haptic_x, haptic_y):
        """Convert haptic coordinates (mm) to screen pixels."""
        screen_x = self.center_x + (haptic_x * self.scale)
        screen_y = self.center_y - (haptic_y * self.scale)  # Invert Y for screen
        return int(screen_x), int(screen_y)
    
    def calculate_distance(self, target_x_mm, target_y_mm, dev_x, dev_y):
        """Calculate Euclidean distance between target and cursor in mm."""
        dx = target_x_mm - dev_x
        dy = target_y_mm - dev_y
        return math.sqrt(dx**2 + dy**2)
    
    def draw_target(self, surface, mouse_x_screen, mouse_y_screen):
        """Draw the target cursor (blue circle at mouse position)."""
        pygame.draw.circle(surface, self.BLUE, (mouse_x_screen, mouse_y_screen), 10)
    
    def draw_user(self, surface, dev_x, dev_y):
        """Draw the user position (red circle)."""
        screen_x, screen_y = self.screen_from_haptic(dev_x, dev_y)
        pygame.draw.circle(surface, self.RED, (screen_x, screen_y), 15)
    
    def draw_status(self, surface, device_state, x, y):
        """Draw the status text."""
        if device_state.button:
            status_text = self.font_large.render("Status: ACTIVE (Guiding towards mouse cursor)", True, (0, 255, 0))
        else:
            status_text = self.font_large.render("Status: DISABLED (Hold Button to feel force)", True, (255, 100, 100))
        surface.blit(status_text, (x, y))
    
    def draw_coordinates(self, surface, target_x_mm, target_y_mm, dev_x, dev_y):
        """Draw the coordinate viewport."""
        target_text = self.font_small.render(f"Target:  X={target_x_mm:7.2f}  Y={target_y_mm:7.2f}", True, self.BLUE)
        cursor_text = self.font_small.render(f"Cursor:  X={dev_x:7.2f}  Y={dev_y:7.2f}", True, self.RED)
        
        surface.blit(target_text, (20, self.height - 60))
        surface.blit(cursor_text, (20, self.height - 30))
    
    def draw_distance(self, surface, mouse_x_screen, mouse_y_screen, dev_x, dev_y, target_x_mm, target_y_mm):
        """Draw a line between cursor and target with distance label."""
        screen_user_x, screen_user_y = self.screen_from_haptic(dev_x, dev_y)
        
        # Draw line connecting the two points
        pygame.draw.line(surface, self.GREEN, (screen_user_x, screen_user_y), (mouse_x_screen, mouse_y_screen), 2)
        
        # Calculate and display distance
        distance = self.calculate_distance(target_x_mm, target_y_mm, dev_x, dev_y)
        distance_text = self.font_small.render(f"Distance: {distance:7.2f} mm", True, self.GREEN)
        surface.blit(distance_text, (self.width - 280, 20))
    
    def render(self, surface, device_state, dev_x, dev_y, mouse_x_screen, mouse_y_screen, target_x_mm, target_y_mm):
        """Render all visual elements."""
        surface.fill(self.BLACK)
        
        self.draw_target(surface, mouse_x_screen, mouse_y_screen)
        self.draw_user(surface, dev_x, dev_y)
        self.draw_distance(surface, mouse_x_screen, mouse_y_screen, dev_x, dev_y, target_x_mm, target_y_mm)
        self.draw_status(surface, device_state, 20, 20)
        self.draw_coordinates(surface, target_x_mm, target_y_mm, dev_x, dev_y)
        
        pygame.display.flip()

# --- 5. Main Visual Loop ---
def main(k_drag=0.08, k_z=0.15):
    """
    Main application loop.
    
    Args:
        k_drag: Stiffness for XY plane guidance (default: 0.08)
        k_z: Stiffness for Z-axis centering (default: 0.15)
    """
    pygame.init()
    width, height = 800, 600
    surface = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Haptic Active Guidance Demo")
    
    clock = pygame.time.Clock()

    print("Initialize Haptic Device...")
    # Initialize OpenHaptics
    device = HapticDevice(device_name="Default Device", callback=state_callback)
    time.sleep(0.2) # Wait for init
    
    # Initialize physics and renderer
    physics_engine = PhysicsEngine(k_drag=k_drag, k_z=k_z)
    renderer = Renderer(width, height)

    run = True
    while run:
        clock.tick(60) # Visuals at 60 FPS
        
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
        target_x_mm, target_y_mm = physics_engine.update(device_state.position, mouse_x_screen, mouse_y_screen, width, height)

        # --- DRAWING ---
        renderer.render(surface, device_state, dev_x, dev_y, mouse_x_screen, mouse_y_screen, target_x_mm, target_y_mm)

    device.close()
    pygame.quit()

if __name__ == "__main__":
    # Adjust stiffness values here:
    # k_drag: Stiffness for XY plane guidance (higher = stronger force)
    # k_z: Stiffness for Z-axis centering (higher = stronger force)
    main(k_drag=0.05, k_z=0.15)