from collections.abc import AsyncGenerator
from a2a.server import AgentExecutor, TaskStore
from a2a.types import (
    CancelTaskRequest,
    CancelTaskResponse,
    JSONRPCErrorResponse,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageStreamingRequest,
    SendMessageStreamingResponse,
    SendMessageStreamingSuccessResponse,
    SendMessageSuccessResponse,
    Task,
    TaskNotCancelableError,
    TaskResubscriptionRequest,
    TextPart,
    UnsupportedOperationError,
)

from agent.file_agent import IOSYSFileAgent
from .helpers import (
    create_task_obj,
    process_streaming_agent_response,
    update_task_with_agent_response,
)


class IOSYSAgentExecutor(AgentExecutor):
    def __init__(self, file_agent: IOSYSFileAgent, task_store: TaskStore):
        self.file_agent = file_agent
        self.task_store = task_store

    async def on_message_send(
        self, request: SendMessageRequest, task: Task | None
    ) -> SendMessageResponse:
        """Handler for 'message/send' requests."""
        params: MessageSendParams = request.params
        query = self._get_user_query(params)

        if not task:
            task = create_task_obj(params)
            await self.task_store.save(task)

        # invoke the underlying agent
        agent_response = dict(await self.file_agent.process(query))

        update_task_with_agent_response(task, agent_response)
        return SendMessageResponse(
            root=SendMessageSuccessResponse(id=request.id, result=task)
        )

    async def on_message_stream(
        self, request: SendMessageStreamingRequest, task: Task | None
    ) -> AsyncGenerator[SendMessageStreamingResponse, None]:
        """Handler for 'message/sendStream' requests."""
        params: MessageSendParams = request.params
        query = self._get_user_query(params)

        if not task:
            task = create_task_obj(params)
            await self.task_store.save(task)

        agent_response = dict(await self.file_agent.process(query))

        task_artifact_update_event, task_status_event = (
            process_streaming_agent_response(task, agent_response)
        )

        if task_artifact_update_event:
            yield SendMessageStreamingResponse(
                root=SendMessageStreamingSuccessResponse(
                    id=request.id, result=task_artifact_update_event
                )
            )

        yield SendMessageStreamingResponse(
            root=SendMessageStreamingSuccessResponse(
                id=request.id, result=task_status_event
            )
        )

    async def on_cancel(
        self, request: CancelTaskRequest, task: Task
    ) -> CancelTaskResponse:
        """Handler for 'tasks/cancel' requests."""
        return CancelTaskResponse(
            root=JSONRPCErrorResponse(id=request.id, error=TaskNotCancelableError())
        )

    async def on_resubscribe(
        self, request: TaskResubscriptionRequest, task: Task
    ) -> AsyncGenerator[SendMessageStreamingResponse, None]:
        """Handler for 'tasks/resubscribe' requests."""
        yield SendMessageStreamingResponse(
            root=JSONRPCErrorResponse(id=request.id, error=UnsupportedOperationError())
        )

    def _get_user_query(self, task_send_params: MessageSendParams) -> str:
        """Helper to get user query from task send params."""
        part = task_send_params.message.parts[0].root
        if not isinstance(part, TextPart):
            raise ValueError("Only text parts are supported")
        return part.text
