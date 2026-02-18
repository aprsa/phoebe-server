"""Session management endpoints."""

from fastapi import APIRouter, HTTPException, Request, Depends
from ..manager import session_manager
from ..auth import get_current_user

router = APIRouter()


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    # Check X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get('X-Forwarded-For', None)
    if forwarded_for is not None:
        return forwarded_for.split(',')[0].strip()
    if request.client:
        return request.client.host
    return 'unknown'


def _check_ownership(session_id: str, user: dict | None):
    """Raise 403 if user doesn't own the session."""
    if user is None:
        return  # auth mode "none" — no ownership check
    owner = session_manager.get_session_owner(session_id)
    if owner is not None and owner != user['user_id']:
        raise HTTPException(status_code=403, detail='You are not the owner of this session')


# ---------- sessions --------------------------------------------------


@router.get('/sessions')
async def list_sessions(user: dict | None = Depends(get_current_user)):
    """List active sessions visible to the current user."""
    user_id = user['user_id'] if user else None
    return session_manager.list_sessions(user_id=user_id)


@router.post('/start-session')
async def start_session(
    request: Request,
    metadata: dict | None = None,
    user: dict | None = Depends(get_current_user),
):
    """Start a new PHOEBE session."""
    client_ip = _get_client_ip(request)
    user_agent = request.headers.get('User-Agent')

    user_id = user['user_id'] if user else None
    full_name = user['full_name'] if user else ''

    try:
        return session_manager.launch_phoebe_worker(
            client_ip=client_ip,
            user_agent=user_agent,
            user_id=user_id,
            full_name=full_name,
            metadata=metadata,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


@router.post('/end-session/{session_id}')
async def end_session(
    session_id: str,
    user: dict | None = Depends(get_current_user),
):
    """End a specific session."""
    _check_ownership(session_id, user)
    success = session_manager.shutdown_server(session_id)
    if not success:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'success': success}


# ---------- memory / ports --------------------------------------------


@router.get('/session-memory')
async def session_memory_all(user: dict | None = Depends(get_current_user)):
    """Get memory usage for all sessions visible to the current user."""
    user_id = user['user_id'] if user else None
    sessions = session_manager.list_sessions(user_id=user_id)
    memory_data = {}
    for session_id in sessions:
        mem_used = session_manager.get_current_memory_usage(session_id)
        if mem_used is not None:
            memory_data[session_id] = mem_used
    return memory_data


@router.post('/session-memory/{session_id}')
async def session_memory(
    session_id: str,
    user: dict | None = Depends(get_current_user),
):
    """Get memory usage for a specific session."""
    _check_ownership(session_id, user)
    mem_used = session_manager.get_current_memory_usage(session_id)
    if mem_used is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'mem_used': mem_used}


@router.get('/port-status')
async def port_status():
    """Get port pool status."""
    return session_manager.get_port_status()
