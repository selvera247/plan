"""Compatibility shim — prefer ``infrastructure.persistence``."""

from infrastructure.persistence import AuditRepository, get_connection, init_db

__all__ = ["get_connection", "init_db", "AuditRepository"]
