"""Compatibility shim — prefer ``infrastructure.llm.assistant``."""
from infrastructure.llm.assistant import *  # noqa: F403
if __name__ == "__main__":
    from infrastructure.llm.assistant import main
    main()
