"""System information endpoints."""

from fastapi import APIRouter, Depends
import phoebe

from ..auth import get_current_user

router = APIRouter()


@router.get('/passbands')
def passbands(user: dict | None = Depends(get_current_user)):
    """Return installed PHOEBE passbands, grouped by passband set."""
    _ = user  # keep auth dependency explicit while supporting auth mode "none"

    items = sorted(phoebe.list_installed_passbands())
    grouped = {}

    for item in items:
        pset, pname = item.split(':', 1)
        grouped.setdefault(pset, []).append(pname)

    return {
        'success': True,
        'result': {
            'passbands': items,
            'grouped': {key: sorted(value) for key, value in sorted(grouped.items())},
        },
    }
