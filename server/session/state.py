"""Session state management. Keeping this in memory for now"""

from __future__ import annotations

from server.models.schemas import SessionContext

_sessions: dict[str, SessionContext] = {}


def get_or_create(session_id: str) -> SessionContext:
    if session_id not in _sessions:
        _sessions[session_id] = SessionContext(session_id=session_id)
    return _sessions[session_id]


def get(session_id: str) -> SessionContext | None:
    return _sessions.get(session_id)


def save(session: SessionContext) -> None:
    _sessions[session.session_id] = session


def delete(session_id: str) -> None:
    _sessions.pop(session_id, None)
