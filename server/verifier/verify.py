"""Claim verifier: cross-references customer statements against CRM data.

Uses Gemini CoT to produce:
  - verdict: verified / disputed / partial / no_record
  - evidence: specific CRM fields that support/contradict the claim
  - recommended_action: what the HITL agent should do next
"""

from __future__ import annotations

import json
import os

from google import genai

from server.models.schemas import SessionContext
from bench import benchmark

SYSTEM_PROMPT = """You are a claim verification agent for an ecommerce company.
You receive customer statements and CRM records in TOON format (compact key:value notation).
Compare the customer's claims against CRM data.

Respond ONLY with JSON in this exact shape:
{
  "verdict": "<one of: verified, disputed, partial, no_record>",
  "evidence": "<specific CRM fields that support or contradict the claim>",
  "recommended_action": "<what the human agent should do next>"
}

Be precise. Cite specific field values from CRM data in your evidence."""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


@benchmark
async def verify(session: SessionContext) -> dict:
    """Run claim verification on a completed FSM session.

    Inputs: session.collected (customer claims) + session.crm_results (CRM data in TOON).
    Output: {verdict, evidence, recommended_action}
    """
    # build TOON context from all CRM results
    crm_context_parts = []
    for query_key, result in session.crm_results.items():
        if "toon" in result:
            crm_context_parts.append(f"[{query_key}]\n{result['toon']}")
    crm_context = "\n\n".join(crm_context_parts)

    user_prompt = f"""Customer statements:
{json.dumps(session.collected, indent=2)}

CRM records (TOON format):
{crm_context}

Issue type: {session.issue_type.value if session.issue_type else 'unknown'}
Verify the customer's claims against the CRM data."""

    client = _get_client()

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=user_prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    return json.loads(response.text)
