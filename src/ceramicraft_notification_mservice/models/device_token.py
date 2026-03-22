import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Use UUID for primary key, stored as a string
pk_guid = Annotated[
    str,
    mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    ),
]

# Use timezone-aware datetime for timestamps
datetime_tz = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True)),
]


class Base(DeclarativeBase):
    pass


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (UniqueConstraint("user_id", "device_id", name="uq_user_device"),)

    id: Mapped[pk_guid]
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fcm_token: Mapped[str] = mapped_column(String(512), nullable=False)
    aes_key: Mapped[str] = mapped_column(String(64), nullable=False)  # Stored as hex
    created_at: Mapped[datetime_tz] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime_tz] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<DeviceToken(id={self.id}, user_id={self.user_id}, "
            f"device_id='{self.device_id}')>"
        )
