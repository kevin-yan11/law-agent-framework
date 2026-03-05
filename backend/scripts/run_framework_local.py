"""Reference non-CopilotKit local client for framework runner.

Example:
    python scripts/run_framework_local.py \
      --message "I got a parking fine yesterday, what can I do?" \
      --state NSW \
      --mode analysis \
      --topic parking_ticket
"""

import argparse
import asyncio
import json

from legal_agent_framework import FrameworkMessage, FrameworkRunRequest, run_framework_turn
from app.agents.conversational_graph import get_conversational_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one local framework turn.")
    parser.add_argument(
        "--message",
        required=True,
        help="Latest user message for the turn.",
    )
    parser.add_argument(
        "--state",
        default="",
        help="Optional jurisdiction/state code (e.g., NSW, VIC).",
    )
    parser.add_argument(
        "--mode",
        default="chat",
        choices=["chat", "analysis"],
        help="UI mode context.",
    )
    parser.add_argument(
        "--topic",
        default="general",
        help="Legal topic context (general, parking_ticket, insurance_claim, ...).",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Optional session ID override.",
    )
    parser.add_argument(
        "--thread-id",
        default="",
        help="Optional thread ID override.",
    )
    parser.add_argument(
        "--trace-id",
        default="",
        help="Optional trace ID to continue an existing trace stream.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    request_context = {
        "user_state": args.state or None,
        "ui_mode": args.mode,
        "legal_topic": args.topic,
    }

    payload = FrameworkRunRequest(
        messages=[FrameworkMessage(role="user", content=args.message)],
        request_context=request_context,
        session_id=args.session_id or None,
        thread_id=args.thread_id or None,
        trace_id=args.trace_id or None,
    )

    result = await run_framework_turn(payload, graph=get_conversational_graph())
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
