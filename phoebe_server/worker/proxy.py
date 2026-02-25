"""ZMQ command proxy."""

import zmq


def send_command(port: int, command: dict, timeout: int = 300) -> dict:
    """Send a command to a PHOEBE worker via ZMQ.

    Args:
        port: Worker port to connect to.
        command: JSON-serializable command dict.
        timeout: Receive timeout in seconds (default 5 min).
    """
    ctx = zmq.Context()
    socket = ctx.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
    socket.setsockopt(zmq.SNDTIMEO, 5000)
    socket.setsockopt(zmq.LINGER, 0)
    try:
        socket.connect(f"tcp://127.0.0.1:{port}")
        socket.send_json(command)
        result = socket.recv_json()
        assert isinstance(result, dict)
        return result
    except zmq.Again:
        return {"success": False, "error": "Worker timed out"}
    finally:
        socket.close()
        ctx.term()
