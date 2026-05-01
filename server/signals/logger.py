"""Signal logger: writes structured signals to DuckDB for analytics.

Every resolved session produces a signal row — issue_type, payment_method,
carrier, verdict, outcome. Query later for spike detection, repeat rate,
carrier failure patterns.
"""

import hashlib

import duckdb

_con: duckdb.DuckDBPyConnection | None = None


def get_signal_db() -> duckdb.DuckDBPyConnection:
    global _con
    if _con is None:
        _con = duckdb.connect("signals.duckdb")
        _con.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY,
                ts TIMESTAMP DEFAULT current_timestamp,
                phone_hash TEXT,
                issue_type TEXT,
                sub_type TEXT,
                payment_method TEXT,
                carrier TEXT,
                region TEXT,
                crm_verdict TEXT,
                outcome TEXT,
                session_id TEXT,
                turn_count INTEGER
            )
        """)
        _con.execute("""
            CREATE SEQUENCE IF NOT EXISTS signal_id_seq START 1
        """)
    return _con


async def log_signal(signal: dict) -> int:
    """Insert a signal row. Returns the signal ID."""
    con = get_signal_db()

    phone = signal.get("phone", "")
    phone_hash = hashlib.sha256(phone.encode()).hexdigest()[:16] if phone else ""

    row_id = con.execute("SELECT nextval('signal_id_seq')").fetchone()[0]

    con.execute("""
        INSERT INTO signals VALUES (?, current_timestamp, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        row_id,
        phone_hash,
        signal.get("issue_type", "unknown"),
        signal.get("sub_type"),
        signal.get("payment_method"),
        signal.get("carrier"),
        signal.get("region"),
        signal.get("crm_verdict"),
        signal.get("outcome"),
        signal.get("session_id"),
        signal.get("turn_count", 0),
    ])

    return row_id
