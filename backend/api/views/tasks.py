from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import (
    TaskCompletionResponseSerializer,
    TaskCreateRequestSerializer,
    TaskListResponseSerializer,
)
from core.errors import AIResponseInvalid


class TaskListCreateView(APIView):
    @extend_schema(
        request=TaskCreateRequestSerializer,
        responses={200: TaskCompletionResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        request_serializer = TaskCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        text = request_serializer.validated_data["text"]

        try:
            task = request.game_context.task_service().complete_task(text)
        except AIResponseInvalid:
            return Response(
                {"error": {"code": "AI_INVALID", "message": "The AI response was invalid."}},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(TaskCompletionResponseSerializer(task).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "days", int, description="How many days of history to return (default 30)"
            )
        ],
        responses={200: TaskListResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        tasks = request.game_context.task_service().list_recent(days=days)
        return Response(TaskListResponseSerializer({"tasks": tasks}).data)
