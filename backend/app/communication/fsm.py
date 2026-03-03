"""Finite State Machine for agent execution orchestration.

Each agent operates in three states: Wait -> Execution -> Finish.
The FSM defines information flow directions between agents.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class FSMState(str, Enum):
    WAIT = "wait"
    EXECUTION = "execution"
    FINISH = "finish"


class AgentFSM:
    """FSM-based execution plan for multi-agent orchestration.

    Nodes represent agents, edges represent information transition directions.
    Each agent has three states: Wait, Execution, Finish.
    """

    def __init__(self):
        self._states: dict[str, FSMState] = {}
        self._transitions: dict[str, list[str]] = defaultdict(list)
        self._reverse_transitions: dict[str, list[str]] = defaultdict(list)

    def add_state(self, agent_name: str, initial_state: FSMState = FSMState.WAIT) -> None:
        self._states[agent_name] = initial_state

    def add_transition(self, from_agent: str, to_agent: str) -> None:
        """Add a directed edge from from_agent to to_agent."""
        if to_agent not in self._transitions[from_agent]:
            self._transitions[from_agent].append(to_agent)
        if from_agent not in self._reverse_transitions[to_agent]:
            self._reverse_transitions[to_agent].append(from_agent)

    def transition(self, agent_name: str, new_state: FSMState) -> None:
        if agent_name not in self._states:
            raise ValueError(f"Unknown agent: {agent_name}")

        current = self._states[agent_name]

        valid_transitions = {
            FSMState.WAIT: {FSMState.EXECUTION},
            FSMState.EXECUTION: {FSMState.FINISH, FSMState.WAIT},
            FSMState.FINISH: set(),
        }

        if new_state not in valid_transitions.get(current, set()):
            logger.warning(
                f"Invalid state transition for {agent_name}: "
                f"{current.value} -> {new_state.value}"
            )

        self._states[agent_name] = new_state
        logger.debug(f"Agent {agent_name}: {current.value} -> {new_state.value}")

    def get_state(self, agent_name: str) -> FSMState:
        return self._states.get(agent_name, FSMState.WAIT)

    def get_successors(self, agent_name: str) -> list[str]:
        return self._transitions.get(agent_name, [])

    def get_predecessors(self, agent_name: str) -> list[str]:
        return self._reverse_transitions.get(agent_name, [])

    def is_ready(self, agent_name: str) -> bool:
        """Check if all predecessors have finished, making this agent ready."""
        predecessors = self.get_predecessors(agent_name)
        return all(
            self._states.get(p) == FSMState.FINISH
            for p in predecessors
        )

    def all_finished(self) -> bool:
        return all(s == FSMState.FINISH for s in self._states.values())

    def get_ready_agents(self) -> list[str]:
        """Return agents that are in WAIT state and whose predecessors are all FINISH."""
        ready = []
        for agent_name, state in self._states.items():
            if state == FSMState.WAIT and self.is_ready(agent_name):
                ready.append(agent_name)
        return ready

    def to_dict(self) -> dict:
        return {
            "states": {k: v.value for k, v in self._states.items()},
            "transitions": dict(self._transitions),
        }
