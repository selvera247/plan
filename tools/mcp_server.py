"""Compatibility shim — prefer ``interfaces.mcp.server``."""
from interfaces.mcp.server import *  # noqa: F403
from interfaces.mcp.server import mcp
__all__ = ["mcp"]
