from typing import Optional
import base64

from fastapi import HTTPException, status


def decode_cursor(cursor_str: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Decodes the base64 cursor string into (created_at_str, id_str)."""
    if not cursor_str:
        return None, None
    try:
        decoded = base64.b64decode(cursor_str.encode()).decode()
        created_at, item_id = decoded.split("|")
        return created_at, item_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor token provided.",
        )


def encode_cursor(created_at, item_id) -> str:
    """Encodes the last item's created_at and id into a base64 string."""
    raw_str = f"{created_at.isoformat()}|{str(item_id)}"
    return base64.b64encode(raw_str.encode()).decode()
