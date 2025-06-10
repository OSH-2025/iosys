from a2a.server import A2AServer, DefaultA2ARequestHandler, InMemoryTaskStore
from a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
import os

from . import description
from .agent_executor import IOSYSAgentExecutor


def get_agent_card():
    """Returns the Agent Card for the File System Agent."""
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill = AgentSkill(
        id=description.id,
        name=description.name,
        description=description.description,
        tags=description.tags,
        examples=description.examples,
    )
    return AgentCard(
        name=description.name,
        description="Helps with manipulating files in the user's file system.",
        url=f"http://localhost:{os.environ["A2A_SERVER_PORT"]}/",
        version="1.0.0",
        defaultInputModes=["text", "text/plain"],
        defaultOutputModes=["text", "text/plain"],
        capabilities=capabilities,
        skills=[skill],
        authentication=AgentAuthentication(schemes=["public"]),
    )


def get_app():
    task_store = InMemoryTaskStore()

    request_handler = DefaultA2ARequestHandler(
        agent_executor=IOSYSAgentExecutor(task_store=task_store),
        task_store=task_store,
    )

    server = A2AServer(
        agent_card=get_agent_card(),
        request_handler=request_handler,
    )
    
    return server.app()

app = get_app()
