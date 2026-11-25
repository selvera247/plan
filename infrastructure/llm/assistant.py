"""
Governed finance assistant.

Uses the OpenAI Chat Completions API with function calling so that all
numeric / rule-based answers come from deterministic Python workflows.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from infrastructure.config.paths import ENV_FILE
from infrastructure.tools.openai_tools import TOOL_DEFINITIONS, execute_tool, get_tool_call_log

load_dotenv(ENV_FILE)


SYSTEM_PROMPT = """You are a governed financial assistant in a home-lab prototype.

CRITICAL RULES:
1. NEVER calculate financial numbers yourself. Do not add, subtract, reconcile,
   or compute percentages in your head or in text.
2. ALWAYS call the appropriate tool for any numeric or rule-based question:
   - Reconciliation / matching / unmatched items → reconcile_transactions
   - Budget vs actual / variance / overspend → analyze_variance
3. ALWAYS mention which workflow was used and its version in your response,
   using the lineage field returned by the tool (e.g. "via reconcile_transactions v1.0.0").
4. Base your narrative ONLY on tool results. If a tool errors, explain the error
   and do not invent numbers.
5. For demo questions about sample data, use the aliases:
   - sample_bank / sample_ledger for reconciliation
   - sample_actuals / sample_budget for variance analysis

Be concise, precise, and transparent about lineage and inputs used.
"""


def _assistant_message_dict(message: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content,
    }
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in message.tool_calls
        ]
    return payload


def _parse_tool_arguments(raw: str | None) -> dict[str, Any]:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


class FinanceAssistant:
    """Multi-turn chat assistant that must route finance math through tools."""

    def __init__(
        self,
        *,
        model: str | None = None,
        client: OpenAI | None = None,
        max_tool_rounds: int = 5,
    ) -> None:
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_tool_rounds = max_tool_rounds
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        self.last_tool_calls: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.last_tool_calls = []

    def _complete(self, *, tool_choice: str = "auto") -> Any:
        return self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=TOOL_DEFINITIONS,
            tool_choice=tool_choice,
        )

    def _dispatch_tool_calls(self, message: Any) -> None:
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = _parse_tool_arguments(tool_call.function.arguments)
            result = execute_tool(name, args)
            self.last_tool_calls.append(
                {"name": name, "arguments": args, "result": result}
            )
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                }
            )

    def ask(self, user_message: str) -> dict[str, Any]:
        """
        Send a user message and return the assistant reply plus tool-call metadata.
        """
        self.messages.append({"role": "user", "content": user_message})
        self.last_tool_calls = []

        for _ in range(self.max_tool_rounds):
            message = self._complete(tool_choice="auto").choices[0].message
            self.messages.append(_assistant_message_dict(message))

            if not message.tool_calls:
                return {
                    "reply": message.content or "",
                    "tool_calls": list(self.last_tool_calls),
                    "tool_log": get_tool_call_log(),
                }

            self._dispatch_tool_calls(message)

        # Safety: too many tool rounds — ask model to wrap up without new tools.
        final = self._complete(tool_choice="none").choices[0].message.content or ""
        self.messages.append({"role": "assistant", "content": final})
        return {
            "reply": final,
            "tool_calls": list(self.last_tool_calls),
            "tool_log": get_tool_call_log(),
        }


def main() -> None:
    """Interactive CLI for the governed finance assistant."""
    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY in the environment or a .env file.")
        sys.exit(1)

    assistant = FinanceAssistant()
    print("Governed Finance Assistant (type 'quit' to exit, 'reset' to clear history)\n")
    while True:
        try:
            user = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user.lower() in {"quit", "exit", "q"}:
            break
        if user.lower() == "reset":
            assistant.reset()
            print("Conversation reset.\n")
            continue

        outcome = assistant.ask(user)
        if outcome["tool_calls"]:
            names = ", ".join(tc["name"] for tc in outcome["tool_calls"])
            print(f"[tools called: {names}]")
        print(f"Assistant> {outcome['reply']}\n")


if __name__ == "__main__":
    main()
