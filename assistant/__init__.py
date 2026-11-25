"""Compatibility shim — prefer ``infrastructure.llm``."""

from infrastructure.llm import SYSTEM_PROMPT, FinanceAssistant

__all__ = ["FinanceAssistant", "SYSTEM_PROMPT"]
