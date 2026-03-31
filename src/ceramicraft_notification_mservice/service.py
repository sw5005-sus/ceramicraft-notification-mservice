import asyncio
import logging

import grpc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import crypto, fcm
from .models.device_token import DeviceToken
from .pb import notification_pb2, notification_pb2_grpc

logger = logging.getLogger(__name__)


class NotificationService(notification_pb2_grpc.NotificationServiceServicer):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def SendUserPush(
        self,
        request: notification_pb2.SendUserPushRequest,
        context: grpc.aio.ServicerContext,
    ) -> notification_pb2.SendUserPushResponse:
        try:
            async with self._session_factory() as session:
                stmt = select(DeviceToken).where(DeviceToken.user_id == request.user_id)
                result = await session.execute(stmt)
                devices = result.scalars().all()

                if not devices:
                    logger.info(f"No devices found for user_id: {request.user_id}")
                    return notification_pb2.SendUserPushResponse(
                        success=True, sent_count=0
                    )

                # Extra caller-supplied metadata forwarded to the app as-is.
                extra_data: dict[str, str] = dict(request.data)

                async def _send_and_track(device: DeviceToken) -> str | None:
                    enc_body = crypto.encrypt_payload(device.aes_key, request.body)
                    success = await fcm.send_push(
                        fcm_token=device.fcm_token,
                        encrypted_body=enc_body,
                        extra_data=extra_data or None,
                    )
                    return device.fcm_token if not success else None

                task_objects = []
                async with asyncio.TaskGroup() as tg:
                    for device in devices:
                        task_objects.append(tg.create_task(_send_and_track(device)))

                results = [t.result() for t in task_objects]

                failed_tokens = [t for t in results if t is not None]
                sent_count = len(devices) - len(failed_tokens)

                return notification_pb2.SendUserPushResponse(
                    success=True,
                    sent_count=sent_count,
                    failed_tokens=failed_tokens,
                )

        except Exception as e:
            logger.exception(f"gRPC SendUserPush failed for user_id: {request.user_id}")
            await context.abort(grpc.StatusCode.INTERNAL, f"Internal server error: {e}")
            return notification_pb2.SendUserPushResponse(success=False)
