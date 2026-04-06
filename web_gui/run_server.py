#!/usr/bin/env python3
"""
Start the haptic experiment server (REST API + WebSocket).

Usage:
    python run_server.py [--rest-port 5000] [--ws-port 5001]
"""
import os
import sys
import socket
import argparse
from pathlib import Path


def check_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return True
        except OSError:
            return False


def find_free_port(start: int, attempts: int = 10) -> int:
    for offset in range(attempts):
        port = start + offset
        if check_port_available(port):
            return port
    raise RuntimeError(f"No free port found between {start} and {start + attempts - 1}")


def main():
    parser = argparse.ArgumentParser(description='Haptic Experiment Server')
    parser.add_argument('--rest-port', type=int, default=5000)
    parser.add_argument('--ws-port', type=int, default=5001)
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    rest_port = find_free_port(args.rest_port)
    ws_port = find_free_port(args.ws_port)

    if rest_port != args.rest_port:
        print(f"Port {args.rest_port} in use, REST API will use {rest_port}")
    if ws_port != args.ws_port:
        print(f"Port {args.ws_port} in use, WebSocket will use {ws_port}")

    # Import and start server inline (same process)
    from app import main as run_app
    run_app(rest_port=rest_port, ws_port=ws_port)


if __name__ == '__main__':
    main()
