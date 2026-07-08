import logging

from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.paginations import MyCustomPaginator
from api.serializer.screener import (
    ScreenshotSerializer,
    ScreenshotUploadSerializer,
    WhitelistUserSerializer,
)
from apps.screener.models import Screenshot, WhitelistUser

logger = logging.getLogger(__name__)


class ScreenshotUploadView(APIView):
    """
    POST /api/v1/screener/upload/
    Принимает один или несколько файлов, сохраняет и ставит задачу на анализ.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        images = request.FILES.getlist("images")
        if not images:
            return Response(
                {"detail": "No images provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ScreenshotUploadSerializer(data={"images": images})
        serializer.is_valid(raise_exception=True)

        from django_q.tasks import async_task

        screenshot_ids = []
        for img in serializer.validated_data["images"]:
            s = Screenshot.objects.create(image=img)
            screenshot_ids.append(s.id)

        async_task(
            "apps.screener.tasks.analyze_screenshots",
            screenshot_ids,
        )
        logger.info("Uploaded %d screenshots, task dispatched.", len(screenshot_ids))

        return Response(
            {
                "detail": f"{len(screenshot_ids)} screenshot(s) queued for analysis.",
                "screenshot_ids": screenshot_ids,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ScreenshotViewSet(ReadOnlyModelViewSet):
    """
    GET /api/v1/screener/screenshots/
    GET /api/v1/screener/screenshots/{id}/
    """
    queryset = Screenshot.objects.select_related("result").all()
    serializer_class = ScreenshotSerializer
    pagination_class = MyCustomPaginator
    permission_classes = [IsAuthenticated]


class WhitelistViewSet(ReadOnlyModelViewSet):
    """
    GET /api/v1/screener/whitelist/  — только для админов
    """
    queryset = WhitelistUser.objects.all()
    serializer_class = WhitelistUserSerializer
    pagination_class = MyCustomPaginator
    permission_classes = [IsAdminUser]
