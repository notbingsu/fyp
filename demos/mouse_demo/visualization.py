#!/usr/bin/env python
"""
Visualization module for haptic experiment data.
Generates graphs and charts from experiment JSON data.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path


class ExperimentVisualizer:
    """Visualizes haptic experiment data."""
    
    def __init__(self, json_filepath):
        """
        Initialize the visualizer with experiment data.
        
        Args:
            json_filepath: Path to the experiment JSON file
        """
        self.json_filepath = json_filepath
        self.data = self._load_json()
        self.metadata = self.data.get("metadata", {})
        self.ticks = self.data.get("ticks", [])
    
    def _load_json(self):
        """Load experiment data from JSON file."""
        with open(self.json_filepath, 'r') as f:
            return json.load(f)
    
    def _extract_arrays(self):
        """Extract data arrays from ticks."""
        times = [tick["elapsed_time"] for tick in self.ticks]
        distances = [tick["distance_mm"] for tick in self.ticks]
        device_x = [tick["device_x"] for tick in self.ticks]
        device_y = [tick["device_y"] for tick in self.ticks]
        target_x = [tick["target_x"] for tick in self.ticks]
        target_y = [tick["target_y"] for tick in self.ticks]
        
        return times, distances, device_x, device_y, target_x, target_y
    
    def plot_distance_over_time(self, figsize=(12, 6)):
        """Plot distance between device and target over time."""
        times, distances, _, _, _, _ = self._extract_arrays()
        
        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(times, distances, linewidth=2, color='#FF6B6B', label='Distance')
        
        # Add statistics
        mean_distance = np.mean(distances)
        max_distance = np.max(distances)
        min_distance = np.min(distances)
        
        ax.axhline(y=mean_distance, color='green', linestyle='--', label=f'Mean: {mean_distance:.2f}mm')
        ax.axhline(y=max_distance, color='orange', linestyle=':', alpha=0.7, label=f'Max: {max_distance:.2f}mm')
        ax.axhline(y=min_distance, color='blue', linestyle=':', alpha=0.7, label=f'Min: {min_distance:.2f}mm')
        
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Distance (mm)', fontsize=12)
        ax.set_title('Euclidean Distance Over Time', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        return fig, ax
    
    def plot_trajectory(self, figsize=(10, 8)):
        """Plot the 2D trajectory of device position vs target."""
        _, _, device_x, device_y, target_x, target_y = self._extract_arrays()
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot trajectories
        ax.plot(device_x, device_y, linewidth=2, color='#FF5252', label='Device Position', alpha=0.8)
        ax.plot(target_x, target_y, linewidth=2, color='#5B9BD5', label='Target Position', alpha=0.8)
        
        # Mark start and end points
        ax.scatter(device_x[0], device_y[0], s=100, color='#FF5252', marker='o', 
                  edgecolors='black', linewidth=2, label='Device Start', zorder=5)
        ax.scatter(device_x[-1], device_y[-1], s=100, color='#FF5252', marker='s', 
                  edgecolors='black', linewidth=2, label='Device End', zorder=5)
        
        ax.scatter(target_x[0], target_y[0], s=100, color='#5B9BD5', marker='o', 
                  edgecolors='black', linewidth=2, label='Target Start', zorder=5)
        ax.scatter(target_x[-1], target_y[-1], s=100, color='#5B9BD5', marker='s', 
                  edgecolors='black', linewidth=2, label='Target End', zorder=5)
        
        ax.set_xlabel('X Position (mm)', fontsize=12)
        ax.set_ylabel('Y Position (mm)', fontsize=12)
        ax.set_title('2D Trajectory: Device vs Target', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')
        ax.axis('equal')
        
        return fig, ax
    
    def plot_position_components(self, figsize=(14, 8)):
        """Plot X and Y position components separately over time."""
        times, _, device_x, device_y, target_x, target_y = self._extract_arrays()
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
        
        # X-axis plot
        ax1.plot(times, device_x, linewidth=2, color='#FF5252', label='Device X')
        ax1.plot(times, target_x, linewidth=2, color='#5B9BD5', label='Target X')
        ax1.set_ylabel('X Position (mm)', fontsize=11)
        ax1.set_title('X Position Over Time', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=10)
        
        # Y-axis plot
        ax2.plot(times, device_y, linewidth=2, color='#FF5252', label='Device Y')
        ax2.plot(times, target_y, linewidth=2, color='#5B9BD5', label='Target Y')
        ax2.set_xlabel('Time (seconds)', fontsize=11)
        ax2.set_ylabel('Y Position (mm)', fontsize=11)
        ax2.set_title('Y Position Over Time', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=10)
        
        plt.tight_layout()
        return fig, (ax1, ax2)
    
    def plot_distance_histogram(self, bins=30, figsize=(10, 6)):
        """Plot histogram of distance values."""
        _, distances, _, _, _, _ = self._extract_arrays()
        
        fig, ax = plt.subplots(figsize=figsize)
        ax.hist(distances, bins=bins, color='#FF6B6B', edgecolor='black', alpha=0.7)
        
        mean_distance = np.mean(distances)
        median_distance = np.median(distances)
        std_distance = np.std(distances)
        
        ax.axvline(mean_distance, color='green', linestyle='--', linewidth=2, 
                  label=f'Mean: {mean_distance:.2f}mm')
        ax.axvline(median_distance, color='orange', linestyle='--', linewidth=2, 
                  label=f'Median: {median_distance:.2f}mm')
        
        ax.set_xlabel('Distance (mm)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title(f'Distance Distribution (σ={std_distance:.2f}mm)', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        return fig, ax
    
    def plot_summary_stats(self, figsize=(10, 6)):
        """Create a text-based summary of experiment statistics."""
        _, distances, device_x, device_y, target_x, target_y = self._extract_arrays()
        
        stats = {
            "Total Duration": f"{self.metadata.get('total_duration_seconds', 0):.2f}s",
            "Total Ticks": self.metadata.get('total_ticks', 0),
            "Avg Tick Rate": f"{self.metadata.get('average_tick_rate', 0):.2f} Hz",
            "Mean Distance": f"{np.mean(distances):.2f}mm",
            "Median Distance": f"{np.median(distances):.2f}mm",
            "Std Dev Distance": f"{np.std(distances):.2f}mm",
            "Min Distance": f"{np.min(distances):.2f}mm",
            "Max Distance": f"{np.max(distances):.2f}mm",
        }
        
        fig, ax = plt.subplots(figsize=figsize)
        ax.axis('off')
        
        y_pos = 0.9
        title = ax.text(0.5, y_pos, "Experiment Summary Statistics", 
                       ha='center', fontsize=16, fontweight='bold')
        
        y_pos -= 0.1
        for key, value in stats.items():
            ax.text(0.1, y_pos, f"{key}:", fontsize=12, fontweight='bold')
            ax.text(0.5, y_pos, str(value), fontsize=12)
            y_pos -= 0.08
        
        return fig, ax
    
    def generate_report(self, output_dir="./experiment_report"):
        """Generate a complete report with all visualizations."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"Generating experiment report in {output_dir}...")
        
        # Plot 1: Distance over time
        fig1, _ = self.plot_distance_over_time()
        fig1.savefig(output_path / "01_distance_over_time.png", dpi=150, bbox_inches='tight')
        plt.close(fig1)
        print("  ✓ Generated: 01_distance_over_time.png")
        
        # Plot 2: Trajectory
        fig2, _ = self.plot_trajectory()
        fig2.savefig(output_path / "02_trajectory.png", dpi=150, bbox_inches='tight')
        plt.close(fig2)
        print("  ✓ Generated: 02_trajectory.png")
        
        # Plot 3: Position components
        fig3, _ = self.plot_position_components()
        fig3.savefig(output_path / "03_position_components.png", dpi=150, bbox_inches='tight')
        plt.close(fig3)
        print("  ✓ Generated: 03_position_components.png")
        
        # Plot 4: Distance histogram
        fig4, _ = self.plot_distance_histogram()
        fig4.savefig(output_path / "04_distance_histogram.png", dpi=150, bbox_inches='tight')
        plt.close(fig4)
        print("  ✓ Generated: 04_distance_histogram.png")
        
        # Plot 5: Summary stats
        fig5, _ = self.plot_summary_stats()
        fig5.savefig(output_path / "05_summary_statistics.png", dpi=150, bbox_inches='tight')
        plt.close(fig5)
        print("  ✓ Generated: 05_summary_statistics.png")
        
        print(f"\nReport complete! All files saved to {output_dir}/")


def visualize_experiment(json_filepath, output_dir="./experiment_report"):
    """
    Convenience function to load and visualize experiment data.
    
    Args:
        json_filepath: Path to the experiment JSON file
        output_dir: Directory to save visualization files
    """
    visualizer = ExperimentVisualizer(json_filepath)
    visualizer.generate_report(output_dir)
    return visualizer


if __name__ == "__main__":
    # Example usage: visualize_experiment("experiment_data.json")
    import sys
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "./experiment_report"
        visualize_experiment(json_file, output_dir)
    else:
        print("Usage: python visualization.py <json_file> [output_dir]")
        print("Example: python visualization.py experiment_data.json ./report")
