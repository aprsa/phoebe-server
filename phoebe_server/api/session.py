"""Session management endpoints."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..manager import session_manager

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    # Check X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get('X-Forwarded-For', None)
    if forwarded_for is not None:
        # X-Forwarded-For can contain multiple IPs, first one is the original client
        return forwarded_for.split(",")[0].strip()
    # Fall back to direct connection IP
    if request.client:
        return request.client.host
    return "unknown"


class UserInfo(BaseModel):
    first_name: str
    last_name: str


@router.get("/sessions")
async def list_sessions():
    """Get all active sessions."""
    # Clean up idle sessions before returning list
    session_manager.cleanup_idle_sessions()
    return session_manager.list_sessions()


@router.post("/start-session")
async def start_session(request: Request):
    """Start a new PHOEBE session."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")
    return session_manager.launch_phoebe_server(client_ip=client_ip, user_agent=user_agent)


@router.post("/end-session/{client_id}")
async def end_session(client_id: str):
    """End a specific session."""
    success = session_manager.shutdown_server(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": success}


@router.post("/update-user-info/{client_id}")
async def update_user_info(client_id: str, user_info: UserInfo):
    """Update user information for a session."""
    success = session_manager.update_session_user_info(
        client_id,
        user_info.first_name,
        user_info.last_name
    )
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


@router.get("/session-memory")
async def session_memory_all():
    """Get memory usage for all sessions."""
    sessions = session_manager.list_sessions()
    memory_data = {}
    for client_id in sessions.keys():
        mem_used = session_manager.get_current_memory_usage(client_id)
        if mem_used is not None:
            memory_data[client_id] = mem_used
    return memory_data


@router.post("/session-memory/{client_id}")
async def session_memory(client_id: str):
    """Get memory usage for a specific session."""
    mem_used = session_manager.get_current_memory_usage(client_id)
    if mem_used is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"mem_used": mem_used}


@router.get("/port-status")
async def port_status():
    """Get port pool status."""
    return session_manager.get_port_status()
