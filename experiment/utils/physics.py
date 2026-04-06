"""
Physics engine for haptic guidance and 3D polyline path management.
"""
import math

class PolylinePath3D:
    """Defines a 3D polyline path with multiple waypoints."""
    def __init__(self, waypoints, completion_threshold=0.5, endpoint_threshold=1.0):
        self.waypoints = waypoints
        self.current_waypoint_index = 0
        self.completion_threshold = completion_threshold
        self.endpoint_threshold = endpoint_threshold
    def get_current_target(self):
        if self.current_waypoint_index < len(self.waypoints):
            return self.waypoints[self.current_waypoint_index]
        return self.waypoints[-1]
    def is_at_endpoint(self, position):
        endpoint = self.waypoints[-1]
        return self.calculate_distance_3d(position, endpoint) <= self.endpoint_threshold
    def calculate_distance_3d(self, pos1, pos2):
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        dz = pos2[2] - pos1[2]
        return math.sqrt(dx**2 + dy**2 + dz**2)
    def update(self, current_position):
        target = self.get_current_target()
        distance = self.calculate_distance_3d(current_position, target)
        if distance <= self.completion_threshold and self.current_waypoint_index < len(self.waypoints) - 1:
            self.current_waypoint_index += 1
            target = self.get_current_target()
            distance = self.calculate_distance_3d(current_position, target)
        progress_ratio = self.current_waypoint_index / (len(self.waypoints) - 1)
        return target, distance, progress_ratio, self.current_waypoint_index

class PhysicsEngine3D:
    """Handles physics calculations for 3D haptic guidance along polyline."""
    def __init__(self, k_xy=0.06, k_z=0.15):
        self.k_xy = k_xy
        self.k_z = k_z
    def calculate_guidance_force(self, dev_pos, target):
        fx = self.k_xy * (target[0] - dev_pos[0])
        fy = self.k_xy * (target[1] - dev_pos[1])
        fz = self.k_z * (target[2] - dev_pos[2])
        return [fx, fy, fz]
