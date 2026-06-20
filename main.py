"""Entry point — command-line interface (CLI).

The user enters two teams; the agent shows live which tools it calls (visible
chain-of-thought) then its final prediction.

Usage:
    python main.py                       # interactive mode
    python main.py "lyon" "marseille"    # teams as arguments
"""

import os
import sys

# On Windows cp1252 consoles, emojis and the "->" arrow break output: force UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from dotenv import load_dotenv

from agents.predictor_agent import DEFAULT_MODEL, build_agent, build_query
from tools.providers import data_source_name
from tools.utils import known_teams

SEP = "─" * 64


def _print_step(node: str, update: dict) -> None:
    """Pretty-print one step of the agent's reasoning."""
    for msg in update.get("messages", []):
        msg_type = msg.__class__.__name__

        # The agent decides to call one or more tools.
        tool_calls = getattr(msg, "tool_calls", None)
        if msg_type == "AIMessage" and tool_calls:
            for call in tool_calls:
                args = ", ".join(f"{k}={v!r}" for k, v in call["args"].items())
                print(f"🔧 Tool call → {call['name']}({args})")
            continue

        # Result returned by a tool.
        if msg_type == "ToolMessage":
            print(f"\n📊 Data [{msg.name}]:")
            for line in str(msg.content).splitlines():
                print(f"   {line}")
            print()
            continue

        # Agent's final message (the reasoning + prediction).
        if msg_type == "AIMessage" and msg.content:
            print(SEP)
            print(msg.content)
            print(SEP)


def run(team_a: str, team_b: str) -> None:
    """Run the agent on a match and stream the reasoning."""
    agent = build_agent()
    query = build_query(team_a, team_b)

    print(f"\n⚽ Match analyzed: {team_a} (home) vs {team_b} (away)")
    print(f"🤖 Model: {DEFAULT_MODEL}")
    print(f"🗄️  Data source: {data_source_name()}")
    print(SEP)
    print("The agent is thinking and consulting its tools...\n")

    for chunk in agent.stream({"messages": [("user", query)]}, stream_mode="updates"):
        for node, update in chunk.items():
            _print_step(node, update)


def _prompt_team(label: str) -> str:
    if "mock" in data_source_name():
        print(f"\nAvailable teams (mock): {', '.join(known_teams())}")
    else:
        print("\nEnter a team's official name (e.g. 'Arsenal FC', 'Real Madrid CF').")
    return input(f"{label}: ").strip()


def main() -> None:
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        print(
            "❌ Missing GROQ_API_KEY.\n"
            "   Copy .env.example to .env and set your Groq key "
            "(free at https://console.groq.com/keys)."
        )
        sys.exit(1)

    if len(sys.argv) >= 3:
        team_a, team_b = sys.argv[1], sys.argv[2]
    else:
        print("=== Explainable sports-prediction agent ===")
        team_a = _prompt_team("Team A (home)")
        team_b = _prompt_team("Team B (away)")

    if not team_a or not team_b:
        print("❌ Please provide two teams.")
        sys.exit(1)

    try:
        run(team_a, team_b)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as exc:  # noqa: BLE001 — clear message for the user
        print(f"\n❌ Error while running the agent: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
