"""Voice agent: STT → server → TTS loop.

Run alongside the FastAPI server to test the full pipeline in real time.
Audio in (mic/file) → Deepgram STT → POST /utterance → ElevenLabs TTS → audio out.

Usage:
    # terminal 1: start server
    uvicorn server.main:app

    # terminal 2: start voice agent
    python -m voice.agent --server http://localhost:8000
"""

from __future__ import annotations

import random
import argparse
import asyncio
import os
from dotenv import load_dotenv

import httpx
from elevenlabs import ElevenLabs
from rich.columns import Columns
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

import bench

console = Console()


SERVER_URL = "http://localhost:8000"

_el: ElevenLabs | None = None

load_dotenv()

def _get_elevenlabs() -> ElevenLabs:
    global _el
    if _el is None:
        _el = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    return _el


@bench.benchmark
async def transcribe(audio_path: str) -> str:
    """ElevenLabs STT: audio file → text. Swap to Deepgram Nova 3 later."""
    el = _get_elevenlabs()

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    result = el.speech_to_text.convert(
        file=audio_data,
        model_id="scribe_v1",
        language_code="eng",
    )

    return result.text


@bench.benchmark
async def call_server(session_id: str, text: str, server_url: str) -> dict:
    """POST /utterance to the resolution server."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{server_url}/utterance",
            json={"session_id": session_id, "text": text},
        )
        resp.raise_for_status()
        return resp.json()


@bench.benchmark
async def synthesize(text: str, output_path: str = "response_{}.mp3") -> str:
    """ElevenLabs TTS: text → audio file."""
    el = _get_elevenlabs()

    num = random.randint(1, 120)
    output_path = output_path.format(num)

    audio = el.text_to_speech.convert(
        text=text,
        voice_id="SAz9YHcvj6GT2YYXdXww",  # default voice, swap as needed
        model_id="eleven_multilingual_v2",
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    return output_path


async def run_turn(session_id: str, audio_path: str, server_url: str) -> dict:
    """One full turn: STT → server → TTS."""
    bench.set_session(session_id)

    transcript = await transcribe(audio_path)
    print(f"[STT] {transcript}")

    response = await call_server(session_id, transcript, server_url)
    response_text = response["response_text"]
    print(f"[SERVER] {response_text}")

    if response_text:
        audio_out = await synthesize(response_text)
        print(f"[TTS] → {audio_out}")

    return response


async def run_session(audio_files: list[str], server_url: str, verbose: bool = False):
    """Run a full conversation: start session, process each audio file as a turn."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{server_url}/session/start")
        session_id = resp.json()["session_id"]

    print(f"Session: {session_id}\n")
    bench.set_session(session_id)

    for i, audio_path in enumerate(audio_files):
        print(f"--- Turn {i + 1} ---")
        response = await run_turn(session_id, audio_path, server_url)

        if response["fsm_state"] in ("verifying", "resolved", "escalated"):
            print(f"\n[FSM] Reached {response['fsm_state']}, ending session.")

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{server_url}/session/{session_id}/end")
                summary = resp.json()

            print_summary(summary, session_id, verbose=verbose)
            break


def print_summary(s: dict, session_id: str, verbose: bool = False):
    """Pretty-print the session summary using rich tables."""
    console.print()

    verdict = s.get("verdict", "unknown")
    color = {"verified": "green", "disputed": "red", "partial": "yellow", "no_record": "dim"}.get(verdict, "white")

    # verdict + evidence + recommendation in one table
    vt = Table(
        title=f"  {verdict.upper()}  ",
        title_style=f"bold {color}",
        show_header=False,
        border_style=color,
        pad_edge=True,
    )
    vt.add_column("Field", style=f"bold {color}", width=20)
    vt.add_column("Value")
    vt.add_row("Session ID", s["session_id"])
    vt.add_row("Issue Type", s.get("issue_type", "—"))
    vt.add_row("Outcome", s.get("signal", {}).get("outcome", "—"))
    vt.add_row("Turns", str(s.get("signal", {}).get("turn_count", "—")))
    vt.add_row("Evidence", s.get("evidence", "—"))
    vt.add_row("Recommendation", s.get("recommended_action", "—"))
    console.print(vt)

    # collected entities table (left)
    ct = Table(title="Collected Entities", border_style="cyan")
    ct.add_column("Entity", style="bold")
    ct.add_column("Value")
    for k, v in s.get("collected", {}).items():
        ct.add_row(k, str(v))

    # CRM data table (right) — deduplicated across query sources
    crm_summary = s.get("crm_summary", "")
    seen_fields: dict[str, str] = {}
    sources_for_field: dict[str, list[str]] = {}
    if crm_summary:
        for line in crm_summary.split("\n"):
            if line.startswith("["):
                bracket_end = line.index("]") + 1
                source = line[1:bracket_end - 1]
                data = line[bracket_end:].strip()
            else:
                source = ""
                data = line.strip()
            if not data:
                continue
            for pair in data.split("\n") if "\n" in data else [data]:
                for field_str in pair.split("\n"):
                    field_str = field_str.strip()
                    if not field_str:
                        continue
                    # TOON lines look like "key: value" or "key: value\nkey: value"
                    parts = [p.strip() for p in field_str.split("\n")]
                    for part in parts:
                        if ": " in part:
                            k, v = part.split(": ", 1)
                            if k not in seen_fields:
                                seen_fields[k] = v
                                sources_for_field[k] = [source]
                            elif source and source not in sources_for_field.get(k, []):
                                sources_for_field.setdefault(k, []).append(source)

    crm = Table(title="CRM Data", border_style="magenta")
    crm.add_column("Field", style="bold magenta")
    crm.add_column("Value")
    for k, v in seen_fields.items():
        crm.add_row(k, v)

    # side by side
    console.print(Columns([ct, crm], padding=(0, 2)))

    # signal + benchmark side by side (optional with --verbose)
    if not verbose:
        return

    signal = s.get("signal", {})
    sig = Table(title="Signal (DuckDB)", border_style="dim")
    sig.add_column("Field", style="bold")
    sig.add_column("Value")
    for k in ("issue_type", "payment_method", "carrier", "region", "crm_verdict", "outcome"):
        sig.add_row(k, str(signal.get(k) or "—"))

    report = bench.get_session_report(session_id)
    bt = Table(title=f"Benchmark — {report['total_ms']}ms total", border_style="cyan")
    bt.add_column("Function", style="bold")
    bt.add_column("Time (ms)", justify="right")
    for call in report["calls"]:
        bt.add_row(call["fn"], f"{call['ms']}")

    console.print(Columns([sig, bt], padding=(0, 2)))


def main():
    parser = argparse.ArgumentParser(description="Voice agent: STT → server → TTS")
    parser.add_argument("audio_files", nargs="+", help="Audio files for each conversation turn")
    parser.add_argument("--server", default=SERVER_URL, help="Server URL")
    args = parser.parse_args()

    asyncio.run(run_session(args.audio_files, args.server))


if __name__ == "__main__":
    main()
