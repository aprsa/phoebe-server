"""Command execution endpoints."""

import time
from fastapi import APIRouter, HTTPException
from ..manager import session_manager
from ..worker.proxy import send_command
from .. import database

router = APIRouter()


@router.post('/send/{client_id}')
async def send(client_id: str, command: dict):
    """Send a command to a PHOEBE session."""
    info = session_manager.get_server_info(client_id)
    if not info:
        raise HTTPException(status_code=404, detail='Invalid client ID')

    # Update activity timestamp
    session_manager.update_last_activity(client_id)

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
        session_id=client_id,
        timestamp=time.time(),
        command_name=command_name,
        success=success,
        execution_time_ms=execution_time_ms,
        error_message=error_message
    )

    # Poll memory after command execution
    session_manager.get_current_memory_usage(client_id)

    return response
