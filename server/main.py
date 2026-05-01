"""talk-to-me: Resolution logic server for voice AI orchestration.

Plug-and-play server that sits after STT in the voice pipeline.
Text in → classify → runbook FSM → CRM verify → summary out.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import FastAPI
from dotenv import load_dotenv

import bench
from server.models.schemas import (
    FSMState,
    SessionSummary,
    UtteranceRequest,
    UtteranceResponse,
)
from server.classifier.gemini import classify
from server.crm.client import CRMClient
from server.fsm.engine import step
from server.session.state import get_or_create, save, get, delete
from server.verifier.verify import verify
from server.signals.logger import log_signal

app = FastAPI(
    title="talk-to-me",
    description="Resolution logic server for voice AI orchestration",
)

load_dotenv()
crm = CRMClient()


@app.post("/session/start")
async def start_session() -> dict:
    """Create a new session. Returns session_id for subsequent calls."""
    session_id = str(uuid.uuid4())
    get_or_create(session_id)
    return {"session_id": session_id}


@app.post("/utterance")
async def handle_utterance(req: UtteranceRequest) -> UtteranceResponse:
    """Process one turn: classify + FSM step + parallel CRM fetch.

    Call this for each STT transcript. Returns next question or signals end.
    """
    bench.set_session(req.session_id)
    session = get_or_create(req.session_id)

    classification = await classify(req.text)

    session, response_text = await step(session, classification, crm.fetch)
    save(session)

    if session.fsm_state in (FSMState.VERIFYING, FSMState.RESOLVED, FSMState.ESCALATED):
        response_text = response_text or "Let me verify this against our records."

    return UtteranceResponse(
        session_id=session.session_id,
        response_text=response_text or "",
        fsm_node=session.fsm_node,
        fsm_state=session.fsm_state,
        crm_data_available=bool(session.crm_results),
    )


@app.post("/session/{session_id}/end")
async def end_session(session_id: str) -> SessionSummary:
    """Finalize session: verify claims, generate summary, log signal.

    Call when FSM reaches VERIFYING/RESOLVED state.
    Returns HITL-ready summary with CRM context in TOON format.
    """
    bench.set_session(session_id)
    session = get(session_id)
    if session is None:
        raise ValueError(f"session {session_id} not found")

    verification, _ = await asyncio.gather(
        verify(session),
        asyncio.sleep(0),
    )

    crm_toon_parts = []
    for query_key, result in session.crm_results.items():
        if "toon" in result:
            crm_toon_parts.append(f"[{query_key}] {result['toon']}")
    crm_summary = "\n".join(crm_toon_parts)

    signal = {
        "session_id": session_id,
        "issue_type": session.issue_type.value if session.issue_type else "unknown",
        "sub_type": None,
        "payment_method": session.collected.get("payment_method"),
        "carrier": session.crm_results.get("get_delivery_status", {}).get("raw", {}).get("carrier"),
        "region": None,
        "crm_verdict": verification["verdict"],
        "outcome": "resolved" if session.fsm_state == FSMState.RESOLVED else "escalated",
        "turn_count": session.turn_count,
    }

    asyncio.create_task(log_signal(signal))

    summary = SessionSummary(
        session_id=session_id,
        issue_type=session.issue_type,
        collected=session.collected,
        crm_summary=crm_summary,
        verdict=verification["verdict"],
        evidence=verification["evidence"],
        recommended_action=verification["recommended_action"],
        signal=signal,
    )

    delete(session_id)
    return summary


@app.get("/bench/{session_id}")
async def get_bench(session_id: str) -> dict:
    """Get benchmark report for a session."""
    return bench.get_session_report(session_id)


@app.get("/bench")
async def get_bench_all() -> dict:
    """Get per-function benchmark stats across all sessions."""
    return bench.get_fn_report()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
