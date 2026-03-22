from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class SendUserPushRequest(_message.Message):
    __slots__ = ("user_id", "title", "body", "data")
    class DataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    user_id: int
    title: str
    body: str
    data: _containers.ScalarMap[str, str]
    def __init__(self, user_id: _Optional[int] = ..., title: _Optional[str] = ..., body: _Optional[str] = ..., data: _Optional[_Mapping[str, str]] = ...) -> None: ...

class SendUserPushResponse(_message.Message):
    __slots__ = ("success", "sent_count", "failed_tokens")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    FAILED_TOKENS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    sent_count: int
    failed_tokens: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, success: bool = ..., sent_count: _Optional[int] = ..., failed_tokens: _Optional[_Iterable[str]] = ...) -> None: ...
