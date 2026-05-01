"""Mock CRM API. Static JSON responses — same shape a real CRM REST API would return.

No database. Just dicts. Swap this entire module for real HTTP calls in production.
"""

ORDERS: dict[str, dict] = {
    "ORD1001": {
        "order_id": "ORD1001",
        "customer_phone": "+917020825816",
        "product": "Noise ColorFit Pro 4",
        "amount": 1799.00,
        "order_status": "payment_failed",
        "payment_method": "UPI",
        "payment_status": "charged",
        "payment_utr": "UTR927364810",
        "carrier": None,
        "tracking_id": None,
        "delivery_attempts": 0,
        "delivery_eta": None,
        "last_delivery_status": None,
        "refund_status": "initiated",
        "refund_amount": 1799.00,
        "refund_eta": "2026-04-30",
        "return_window_end": None,
    },
    "ORD1002": {
        "order_id": "ORD1002",
        "customer_phone": "+917020825816",
        "product": "Samsung Galaxy Buds FE",
        "amount": 4999.00,
        "order_status": "in_transit",
        "payment_method": "card",
        "payment_status": "success",
        "payment_utr": "TXN84729301",
        "carrier": "Delhivery",
        "tracking_id": "DL928374650",
        "delivery_attempts": 1,
        "delivery_eta": "2026-04-28",
        "last_delivery_status": "at_hub_delhi",
        "refund_status": None,
        "refund_amount": None,
        "refund_eta": None,
        "return_window_end": "2026-05-10",
    },
    "ORD1003": {
        "order_id": "ORD1003",
        "customer_phone": "+919876543210",
        "product": "boAt Airdopes 141",
        "amount": 1299.00,
        "order_status": "delivered",
        "payment_method": "UPI",
        "payment_status": "success",
        "payment_utr": "UTR112233445",
        "carrier": "BlueDart",
        "tracking_id": "BD77281930",
        "delivery_attempts": 1,
        "delivery_eta": "2026-04-24",
        "last_delivery_status": "delivered",
        "refund_status": None,
        "refund_amount": None,
        "refund_eta": None,
        "return_window_end": "2026-05-04",
    },
    "ORD1004": {
        "order_id": "ORD1004",
        "customer_phone": "+919876543210",
        "product": "Realme Buds Air 5",
        "amount": 2499.00,
        "order_status": "delivered",
        "payment_method": "net_banking",
        "payment_status": "success",
        "payment_utr": "NB998877665",
        "carrier": "DTDC",
        "tracking_id": "DT55039281",
        "delivery_attempts": 2,
        "delivery_eta": "2026-04-23",
        "last_delivery_status": "delivered_wrong_item",
        "refund_status": "not_initiated",
        "refund_amount": None,
        "refund_eta": None,
        "return_window_end": "2026-05-03",
    },
}

# field subsets per query type — mirrors what a real API would scope per endpoint
QUERY_FIELDS: dict[str, list[str]] = {
    "get_payment_status": ["order_id", "payment_method", "payment_status", "payment_utr", "amount"],
    "get_transaction_details": ["order_id", "payment_method", "payment_status", "payment_utr", "order_status", "amount"],
    "get_refund_status": ["order_id", "refund_status", "refund_amount", "refund_eta", "payment_utr"],
    "get_delivery_status": ["order_id", "carrier", "tracking_id", "delivery_eta", "last_delivery_status", "order_status"],
    "get_delivery_attempts": ["order_id", "carrier", "tracking_id", "delivery_attempts", "last_delivery_status", "delivery_eta"],
    "get_order_details": ["order_id", "product", "amount", "order_status", "delivery_eta"],
    "get_return_window": ["order_id", "product", "return_window_end", "order_status", "last_delivery_status"],
    "get_service_appointment": ["order_id", "order_status", "carrier"],
}


def query(query_key: str, order_id: str) -> dict | None:
    """Simulate a CRM API call. Returns scoped JSON or None if not found."""
    order = ORDERS.get(order_id)
    if order is None:
        return None
    fields = QUERY_FIELDS.get(query_key)
    if fields is None:
        return None
    return {k: order[k] for k in fields if k in order}
