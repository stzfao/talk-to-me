from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class IssueType(str, Enum):
    PAYMENT_FAILED = "payment_failed"
    ITEM_NOT_DELIVERED = "item_not_delivered"
    WRONG_ITEM = "wrong_item"
    REFUND_DELAYED = "refund_delayed"
    AGENT_NO_SHOW = "agent_no_show"
    UNKNOWN = "unknown"


class Classification(BaseModel):
    issue_type: IssueType
    sub_type: str | None = None
    confidence: float
    extracted_entities: dict = {}  # order_id, payment_method, etc. pulled from utterance


class FSMState(str, Enum):
    COLLECTING = "collecting"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class SessionContext(BaseModel):
    session_id: str
    issue_type: IssueType | None = None
    fsm_node: str = "start"
    fsm_state: FSMState = FSMState.COLLECTING
    collected: dict = {}           # answers gathered per runbook step
    crm_results: dict = {}         # pre-fetched CRM data keyed by node
    turn_count: int = 0


class UtteranceRequest(BaseModel):
    session_id: str
    text: str                      # post-STT transcript


class UtteranceResponse(BaseModel):
    session_id: str
    response_text: str             # goes to TTS on caller side
    fsm_node: str
    fsm_state: FSMState
    crm_data_available: bool = False


class SessionSummary(BaseModel):
    session_id: str
    issue_type: IssueType
    collected: dict
    crm_summary: str               # TOON-formatted CRM context
    verdict: str                    # verified / disputed / partial / no_record
    evidence: str
    recommended_action: str
    signal: dict                    # for DuckDB logging
