import asyncio
import json
import logging

import grpc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import crypto, fcm
from .models.device_token import DeviceToken
from .pb import notification_pb2, notification_pb2_grpc

logger = logging.getLogger(__name__)


class NotificationService(notification_pb2_grpc.NotificationServiceServicer):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
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

                payload_dict = {
                    "title": request.title,
                    "body": request.body,
                    "data": dict(request.data),
                }
                payload_json = json.dumps(payload_dict)

                async def _send_and_track(device: DeviceToken):
                    encrypted_payload = crypto.encrypt_payload(
                        device.aes_key, payload_json
                    )
                    success = await fcm.send_push(device.fcm_token, encrypted_payload)
                    return device.fcm_token if not success else None

                tasks = [_send_and_track(device) for device in devices]
                results = await asyncio.gather(*tasks)

                failed_tokens = [token for token in results if token is not None]
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
