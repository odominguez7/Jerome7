"""Agent Mesh Network — inter-agent communication and collective intelligence.

The mesh connects every user's personal agent into a network that enables:
- Agent-to-agent messaging (A2A protocol)
- Accountability pairing
- Collective insight generation
- Proactive intervention detection
"""

from src.agents.mesh.agent_mesh import AgentMesh
from src.agents.mesh.agent_registry import AgentRegistry
from src.agents.mesh.a2a_protocol import A2AProtocol
from src.agents.mesh.message_bus import MessageBus
from src.agents.mesh.collective_insights import CollectiveInsights

__all__ = [
    "AgentMesh",
    "AgentRegistry",
    "A2AProtocol",
    "MessageBus",
    "CollectiveInsights",
]
