"""Runbook definitions: per issue_type, each node defines what to ask and what to pre-fetch from CRM.

Structure:
    node_id -> {
        "ask": question text (None if no more questions),
        "crm": CRM query key to fire in parallel (None if nothing to fetch),
        "extract": list of entity keys to pull from the utterance,
        "next": next node_id (or None for terminal),
    }
"""

RUNBOOKS: dict[str, dict[str, dict]] = {
    "payment_failed": {
        "start": {
            "ask": "Can you share your order ID or the amount you were charged?",
            "crm": None,
            "extract": ["order_id", "amount"],
            "next": "have_order_id",
        },
        "have_order_id": {
            "ask": "Which payment method did you use — UPI, card, or net banking?",
            "crm": "get_payment_status",
            "extract": ["payment_method"],
            "next": "have_payment_method",
        },
        "have_payment_method": {
            "ask": "Did you see an error message or did the app just time out?",
            "crm": "get_transaction_details",
            "extract": ["error_description"],
            "next": "end",
        },
        "end": {
            "ask": None,
            "crm": "get_refund_status",
            "extract": [],
            "next": None,
        },
    },
    "item_not_delivered": {
        "start": {
            "ask": "Can you share your order ID?",
            "crm": None,
            "extract": ["order_id"],
            "next": "have_order_id",
        },
        "have_order_id": {
            "ask": "When was the expected delivery date?",
            "crm": "get_delivery_status",
            "extract": ["expected_date"],
            "next": "have_dates",
        },
        "have_dates": {
            "ask": "Did you receive any delivery attempt notification?",
            "crm": "get_delivery_attempts",
            "extract": ["attempt_notification"],
            "next": "end",
        },
        "end": {
            "ask": None,
            "crm": "get_delivery_attempts",
            "extract": [],
            "next": None,
        },
    },
    "wrong_item": {
        "start": {
            "ask": "Can you share your order ID?",
            "crm": None,
            "extract": ["order_id"],
            "next": "have_order_id",
        },
        "have_order_id": {
            "ask": "What did you receive versus what you ordered?",
            "crm": "get_order_details",
            "extract": ["received_item", "ordered_item"],
            "next": "have_details",
        },
        "have_details": {
            "ask": None,
            "crm": "get_return_window",
            "extract": [],
            "next": None,
        },
    },
    "refund_delayed": {
        "start": {
            "ask": "Can you share your order ID or refund reference number?",
            "crm": None,
            "extract": ["order_id", "refund_ref"],
            "next": "have_order_id",
        },
        "have_order_id": {
            "ask": "When was the refund initiated?",
            "crm": "get_refund_status",
            "extract": ["refund_date"],
            "next": "end",
        },
        "end": {
            "ask": None,
            "crm": "get_refund_status",
            "extract": [],
            "next": None,
        },
    },
    "agent_no_show": {
        "start": {
            "ask": "What was your scheduled time slot?",
            "crm": None,
            "extract": ["time_slot"],
            "next": "have_slot",
        },
        "have_slot": {
            "ask": "Did the agent call you or show any notification?",
            "crm": "get_service_appointment",
            "extract": ["agent_contact"],
            "next": "end",
        },
        "end": {
            "ask": None,
            "crm": "get_service_appointment",
            "extract": [],
            "next": None,
        },
    },
}
