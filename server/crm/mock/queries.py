"""Mock CRM query executor. Returns raw JSON only.

TOON conversion happens in CRMClient, not here.
This module simulates what a real CRM API would return.
"""

from server.crm.mock.api import query


def crm_fetch(query_key: str, collected: dict) -> dict:
    """Execute a mock CRM query. Returns raw JSON."""
    order_id = collected.get("order_id")
    if order_id is None:
        return {"pending": "no order_id collected yet"}

    result = query(query_key, order_id)

    if result is None:
        return {"no_record": True, "order_id": order_id}

    return result
