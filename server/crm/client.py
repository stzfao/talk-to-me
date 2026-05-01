"""CRM Client connector. TOON conversion happens here at the boundary
before data reaches the LLM. Mock for now, swap to real HTTP calls in production.
"""

from server.crm.mock import queries
from server.crm.toon import to_toon
from bench import benchmark


class CRMClient:
    def __init__(self):
        # add auth here
        pass

    def get_issue_by_id(self):
        pass

    def get_customer_profile_by_id(self):
        pass

    @staticmethod
    @benchmark
    async def fetch(query_key: str, collected: dict) -> dict:
        """Fetch from CRM and convert to TOON. This is the function injected into FSM.

        Raw JSON comes from the CRM (mock or real). TOON conversion
        happens here so every CRM backend gets the same treatment.
        """
        raw = queries.crm_fetch(query_key, collected)

        # pass through non-data responses (pending, no_record, error)
        if "pending" in raw or "no_record" in raw or "error" in raw:
            return raw

        return {"toon": to_toon(raw), "raw": raw}
