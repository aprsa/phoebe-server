"""Command execution endpoints."""

import time
from fastapi import APIRouter, HTTPException, Depends
from ..manager import session_manager
from ..worker.proxy import send_command
from .. import database
from ..auth import get_current_user

router = APIRouter()


@router.post("/send/{session_id}")
async def send(
    session_id: str,
    command: dict,
    user: dict | None = Depends(get_current_user),
):
    """Send a command to a PHOEBE session."""
    info = session_manager.get_server_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Invalid session ID")

    # Ownership check
    if user is not None:
        owner = info.get('user_id')
        if owner is not None and owner != user['user_id']:
            raise HTTPException(status_code=403, detail='You are not the owner of this session')

    # Update activity timestamp
    session_manager.update_last_activity(session_id)

    port = info['port']
    command_name = command.get('command', 'unknown')

    # Send command and measure execution time
    start_time = time.time()
    response = send_command(port, command)
    execution_time_ms = (time.time() - start_time) * 1000

    # Log command execution to database
    success = response.get('success', False)
    error_message = response.get('error') if not success else None

    database.log_command_execution(
        session_id=session_id,
        timestamp=time.time(),
        command_name=command_name,
        success=success,
        execution_time_ms=execution_time_ms,
        error_message=error_message
    )

    # Poll memory after command execution
    session_manager.get_current_memory_usage(session_id)

    return response
