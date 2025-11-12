from __future__ import annotations

import sys
from types import ModuleType

import pytest

from api.dependencies import get_queue


class _RedisStub:
    def __init__(self) -> None:
        self.closed = False

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        self.closed = True


def test_get_redis_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[_RedisStub] = []

    def _from_url(
        _url: str, *, encoding: str, decode_responses: bool, **_kwargs: object
    ) -> _RedisStub:
        stub = _RedisStub()
        created.append(stub)
        return stub

    import api.dependencies as deps

    monkeypatch.setattr(
        deps, "Redis", type("R", (), {"from_url": staticmethod(_from_url)})
    )

    gen = deps.get_redis(deps.get_settings())
    client = next(gen)
    assert isinstance(client, _RedisStub)
    with pytest.raises(StopIteration):
        gen.send(None)
    assert created
    assert created[0].closed is True


def test_get_queue_returns_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Q:
        def __init__(self, *, connection: object) -> None:
            self.connection = connection

    class _RQModule(ModuleType):
        Queue: type[_Q]

    dummy = _RQModule("rq")
    dummy.Queue = _Q
    sys.modules["rq"] = dummy

    q = get_queue(_RedisStub())
    assert isinstance(q, _Q)
