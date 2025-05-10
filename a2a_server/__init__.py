import os
import sys

from .agent_executor import CurrencyAgentExecutor

from a2a.server import A2AServer, DefaultA2ARequestHandler, InMemoryTaskStore
from a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

def start_a2a(host: str, port: int):
    task_store = InMemoryTaskStore()

    request_handler = DefaultA2ARequestHandler(
        agent_executor=CurrencyAgentExecutor(task_store=task_store),
        task_store=task_store,
    )

    server = A2AServer(
        agent_card=get_agent_card(host, port), request_handler=request_handler
    )
    server.start(host=host, port=port)

def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Currency Agent."""
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill = AgentSkill(
        id='convert_currency',
        name='Currency Exchange Rates Tool',
        description='Helps with exchange values between various currencies',
        tags=['currency conversion', 'currency exchange'],
        examples=['What is exchange rate between USD and GBP?'],
    )
    return AgentCard(
        name='Currency Agent',
        description='Helps with exchange rates for currencies',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text', 'text/plain'],
        defaultOutputModes=['text', 'text/plain'],
        capabilities=capabilities,
        skills=[skill],
        authentication=AgentAuthentication(schemes=['public']),
    )
