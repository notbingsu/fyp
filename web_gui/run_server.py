#!/usr/bin/env python3
"""
Server startup script for Haptic Experiment Web GUI.
Opens the web interface in the default browser automatically.
"""

import os
import sys
import time
import socket
import webbrowser
import subprocess
from pathlib import Path

def check_port_available(port=5000):
    """Check if the specified port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return True
        except OSError:
            return False

def wait_for_server(host='localhost', port=5000, timeout=10):
    """Wait for the server to start responding."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, port))
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(0.5)
    return False

def main():
    """Start the Flask server and open browser."""
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("=" * 60)
    print("Haptic Experiment Web GUI")
    print("=" * 60)
    print()
    
    # Find available port
    port = 5000
    max_attempts = 10
    
    for attempt in range(max_attempts):
        if check_port_available(port):
            print(f"✓ Port {port} is available")
            break
        else:
            print(f"⚠️  Port {port} is in use, trying {port + 1}...")
            port += 1
    else:
        print(f"❌ No available ports found between 5000-{5000 + max_attempts - 1}")
        sys.exit(1)
    
    print(f"✓ Starting Flask server on port {port}...")
    print()
    
    # Start the Flask app
    try:
        # Use subprocess to run Flask
        process = subprocess.Popen(
            [sys.executable, 'app.py', '--port', str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Wait for server to be ready
        print("⏳ Waiting for server to start...")
        if wait_for_server(port=port):
            print("✓ Server is ready!")
            print()
            print("=" * 60)
            print(f"🌐 Web GUI is now running at: http://localhost:{port}")
            print("=" * 60)
            print()
            print("📋 Instructions:")
            print("   1. The web interface will open in your default browser")
            print("   2. Enter a participant ID and configure settings")
            print("   3. Click 'Start Experiment' to begin")
            print("   4. Complete the task in the Pygame window")
            print("   5. View results and export reports")
            print()
            print("⚠️  Press Ctrl+C to stop the server")
            print("=" * 60)
            print()
            
            # Open browser
            time.sleep(1)
            url = f"http://localhost:{port}"
            print(f"🚀 Opening browser: {url}")
            webbrowser.open(url)
            
            # Keep the script running and show Flask output
            try:
                for line in process.stdout:
                    print(line, end='')
            except KeyboardInterrupt:
                print("\n\n⏹️  Shutting down server...")
                process.terminate()
                process.wait()
                print("✓ Server stopped successfully")
        else:
            print("❌ Server failed to start within timeout period")
            process.terminate()
            sys.exit(1)
            
    except FileNotFoundError:
        print("❌ Error: app.py not found in current directory")
        print(f"   Current directory: {script_dir}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
