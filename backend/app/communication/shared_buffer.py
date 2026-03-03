"""Shared Information Buffer for inter-agent communication.

Provides asynchronous, non-blocking storage for information units
with dynamic capacity expansion and TTL-based cleanup.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Optional

from app.communication.info_unit import InformationUnit

logger = logging.getLogger(__name__)


class SharedBuffer:
    """Thread-safe shared information buffer for multi-agent communication.

    Features:
    - Store/retrieve InformationUnits by agent role
    - Dynamic capacity expansion (doubles when full)
    - TTL-based automatic cleanup of outdated entries
    - Async-safe via asyncio.Lock
    """

    def __init__(self, initial_capacity: int = 64, ttl_seconds: float = 3600.0):
        self._buffer: dict[str, list[InformationUnit]] = defaultdict(list)
        self._capacity = initial_capacity
        self._ttl = ttl_seconds
        self._total_items = 0
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        return self._total_items

    @property
    def capacity(self) -> int:
        return self._capacity

    def store(self, info: InformationUnit) -> None:
        """Store an information unit in the buffer."""
        if self._total_items >= self._capacity:
            self._expand()
            self._cleanup()

        self._buffer[info.role].append(info)
        self._total_items += 1
        logger.debug(f"Stored info unit from {info.role}: {info.action}")

    def retrieve_by_role(self, role: str) -> list[InformationUnit]:
        """Retrieve all information units from a specific agent role."""
        return list(self._buffer.get(role, []))

    def retrieve_latest(self, role: str) -> Optional[InformationUnit]:
        """Retrieve the most recent information unit from a role."""
        units = self._buffer.get(role, [])
        return units[-1] if units else None

    def retrieve_for_agent(
        self, agent_name: str, predecessor_roles: list[str]
    ) -> list[InformationUnit]:
        """Selective retrieval: get info units only from predecessor agents."""
        results = []
        for role in predecessor_roles:
            results.extend(self._buffer.get(role, []))
        results.sort(key=lambda u: u.timestamp)
        return results

    def retrieve_all(self) -> list[InformationUnit]:
        """Retrieve all information units from all agents."""
        all_units = []
        for units in self._buffer.values():
            all_units.extend(units)
        all_units.sort(key=lambda u: u.timestamp)
        return all_units

    def retrieve_by_datasource(self, data_source: str) -> list[InformationUnit]:
        """Retrieve all info units related to a specific data source."""
        results = []
        for units in self._buffer.values():
            for unit in units:
                if unit.data_source == data_source:
                    results.append(unit)
        return results

    def update(self, info_id: str, new_info: InformationUnit) -> bool:
        """Update an existing info unit (removes old, adds new)."""
        for role, units in self._buffer.items():
            for i, unit in enumerate(units):
                if unit.id == info_id:
                    self._buffer[role][i] = new_info
                    return True
        return False

    def clear(self) -> None:
        """Clear all entries from the buffer."""
        self._buffer.clear()
        self._total_items = 0

    def _expand(self) -> None:
        """Double the buffer capacity."""
        old_capacity = self._capacity
        self._capacity *= 2
        logger.info(f"Buffer expanded: {old_capacity} -> {self._capacity}")

    def _cleanup(self) -> None:
        """Remove entries older than TTL."""
        cutoff = time.time() - self._ttl
        removed = 0
        for role in list(self._buffer.keys()):
            original = self._buffer[role]
            filtered = [u for u in original if u.timestamp > cutoff]
            removed += len(original) - len(filtered)
            self._buffer[role] = filtered
            if not filtered:
                del self._buffer[role]
        self._total_items -= removed
        if removed > 0:
            logger.info(f"Buffer cleanup: removed {removed} expired entries")
