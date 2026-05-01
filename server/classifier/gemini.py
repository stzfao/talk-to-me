"""Issue classifier using Gemini structured output. BERT will not need this.

Phase 1: Gemini with response_schema for structured classification.
Phase 2: Swap in fine-tuned BERT for latency/cost reduction.
"""

import json
import os

from google import genai

from server.models.schemas import Classification, IssueType
from bench import benchmark

ISSUE_TAXONOMY = {
    "payment_failed": {
        "description": "Payment was charged but order not placed, double charge, UPI/card failure",
        "sub_types": ["charged_no_order", "double_charge", "payment_gateway_error", "upi_timeout"],
    },
    "item_not_delivered": {
        "description": "Order not received past ETA, stuck in transit, no delivery attempt",
        "sub_types": ["past_eta", "stuck_in_transit", "no_attempt", "wrong_address"],
    },
    "wrong_item": {
        "description": "Received different product, wrong size/color, damaged item",
        "sub_types": ["different_product", "wrong_variant", "damaged", "empty_box"],
    },
    "refund_delayed": {
        "description": "Refund initiated but not received, past SLA",
        "sub_types": ["past_sla", "partial_refund", "wrong_account", "not_initiated"],
    },
    "agent_no_show": {
        "description": "Service agent didn't arrive, wrong time slot, no contact",
        "sub_types": ["no_arrival", "wrong_slot", "no_call", "cancelled_without_notice"],
    },
}

SYSTEM_PROMPT = f"""You are an ecommerce customer complaint classifier.
Given a customer utterance, classify it into an issue_type and sub_type.
Extract any entities mentioned (order_id, payment_method, amount, etc).

Issue taxonomy:
{json.dumps(ISSUE_TAXONOMY, indent=2)}

Respond ONLY with JSON in this exact shape:
{{
  "issue_type": "<one of: payment_failed, item_not_delivered, wrong_item, refund_delayed, agent_no_show, unknown>",
  "sub_type": "<sub_type from the taxonomy or null>",
  "confidence": <0.0 to 1.0>,
  "extracted_entities": {{<key: value pairs extracted from the utterance>}}
}}"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


@benchmark
async def classify(text: str) -> Classification:
    """Classify a customer utterance into issue_type + sub_type."""
    client = _get_client()

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=text,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    data = json.loads(response.text)

    return Classification(
        issue_type=IssueType(data["issue_type"]),
        sub_type=data.get("sub_type"),
        confidence=data.get("confidence", 0.8),
        extracted_entities=data.get("extracted_entities", {}),
    )
