"""Communication Protocol for coordinated multi-agent information sharing.

Combines the SharedBuffer and FSM to implement selective retrieval:
agents only receive relevant information from their predecessors.
"""

from __future__ import annotations

import logging
from typing import Any

from app.communication.fsm import AgentFSM, FSMState
from app.communication.info_unit import InformationUnit
from app.communication.shared_buffer import SharedBuffer

logger = logging.getLogger(__name__)


class CommunicationProtocol:
    """Orchestrates information sharing among agents using FSM-based selective retrieval."""

    def __init__(self):
        self.buffer = SharedBuffer()
        self.fsm = AgentFSM()

    def setup_plan(self, execution_plan: list[dict[str, Any]]) -> None:
        """Initialize the FSM from an execution plan."""
        for step in execution_plan:
            agent_name = step["agent"]
            self.fsm.add_state(agent_name, FSMState.WAIT)
            for dep in step.get("depends_on", []):
                self.fsm.add_transition(dep, agent_name)

    def prepare_context(self, agent_name: str) -> list[InformationUnit]:
        """Retrieve relevant information for an agent based on FSM topology."""
        predecessors = self.fsm.get_predecessors(agent_name)

        role_mapping = {
            "sql_agent": "SQL Agent",
            "python_agent": "Python Agent",
            "chart_agent": "Chart Agent",
            "insight_agent": "Insight Agent",
            "eda_agent": "EDA Agent",
            "cleaning_agent": "Cleaning Agent",
            "report_agent": "Report Agent",
        }

        predecessor_roles = [role_mapping.get(p, p) for p in predecessors]
        return self.buffer.retrieve_for_agent(agent_name, predecessor_roles)

    def store_result(self, info: InformationUnit) -> None:
        """Store an agent's output in the shared buffer."""
        self.buffer.store(info)

    def start_agent(self, agent_name: str) -> None:
        self.fsm.transition(agent_name, FSMState.EXECUTION)

    def finish_agent(self, agent_name: str) -> None:
        self.fsm.transition(agent_name, FSMState.FINISH)

    def get_next_agents(self) -> list[str]:
        return self.fsm.get_ready_agents()

    def is_complete(self) -> bool:
        return self.fsm.all_finished()

    def reset(self) -> None:
        self.buffer.clear()
        self.fsm = AgentFSM()
