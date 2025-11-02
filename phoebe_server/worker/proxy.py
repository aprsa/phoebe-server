"""ZMQ command proxy."""

import zmq


def send_command(port: int, command: dict) -> dict:
    """Send a command to a PHOEBE worker via ZMQ."""
    ctx = zmq.Context()
    socket = ctx.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{port}")
    socket.send_json(command)
    reply = socket.recv_json()
    socket.close()
    return reply
