"""FSM engine: advances session state through runbook nodes.

Each turn:
  1. Receives classified utterance + extracted entities
  2. Stores entities in session
  3. Skips nodes whose required entities are already collected
  4. Fires CRM queries for each skipped node in parallel
  5. Returns next unanswered question or signals FSM end
"""

from __future__ import annotations

import asyncio

from server.models.schemas import Classification, FSMState, SessionContext
from server.fsm.runbooks import RUNBOOKS


async def step(
    session: SessionContext,
    classification: Classification,
    crm_fetch: callable,  # async fn(query_key, collected) -> dict
) -> tuple[SessionContext, str | None]:
    """Advance FSM, skipping nodes whose entities are already collected."""
    if session.issue_type is None:
        session.issue_type = classification.issue_type

    runbook = RUNBOOKS.get(session.issue_type.value)
    if runbook is None:
        session.fsm_state = FSMState.ESCALATED
        return session, "I'll connect you with an agent who can help with this."

    node = runbook.get(session.fsm_node)
    if node is None:
        session.fsm_state = FSMState.RESOLVED
        return session, None

    # store extracted entities from this utterance
    session.collected.update(classification.extracted_entities)
    session.turn_count += 1

    # walk forward through nodes, skipping any whose extract keys are already satisfied
    crm_tasks = []
    current_node = node

    while True:
        # fire CRM pre-fetch for this node if applicable
        if current_node["crm"]:
            crm_tasks.append(
                (current_node["crm"], asyncio.create_task(
                    crm_fetch(current_node["crm"], session.collected)
                ))
            )

        next_node_id = current_node["next"]
        next_node = runbook.get(next_node_id) if next_node_id else None

        # terminal: no more nodes
        if next_node is None or next_node["ask"] is None:
            # collect all CRM results
            for key, task in crm_tasks:
                session.crm_results[key] = await task
            session.fsm_node = next_node_id or session.fsm_node
            session.fsm_state = FSMState.VERIFYING
            return session, None

        # check if next node's required entities are already collected
        required = next_node.get("extract", [])
        has_all = required and all(k in session.collected for k in required)

        if has_all:
            # skip this node — entities already provided
            current_node = next_node
            continue

        # stop here — need to ask this question
        for key, task in crm_tasks:
            session.crm_results[key] = await task
        session.fsm_node = next_node_id
        return session, next_node["ask"]
