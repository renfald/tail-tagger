from typing import TypeAlias, TYPE_CHECKING

from ._compat import Self

from torch import Tensor, device, get_default_device

try:
    from torch.cuda import Event, Stream, current_stream, set_stream
except ImportError:
    if not TYPE_CHECKING:
        from types import NoneType
        Event = NoneType
        Stream = NoneType

__all__ = ("CuFork",)

class CuFork:
    def __init__(self, stream: Stream | Tensor | device | str | None = None) -> None:
        self.stream: Stream | None = None
        self.forked: Stream | None = None
        self.event: Event | None = None

        if isinstance(stream, Stream):
            self.stream = stream
        else:
            if isinstance(stream, Tensor):
                dev = stream.device
            elif isinstance(stream, str):
                dev = device(stream)
            elif stream is None:
                dev = get_default_device()
            else:
                dev = stream

            if dev.type == "cuda":
                self.stream = current_stream(dev)

    def __enter__(self) -> Self:
        if self.stream is not None:
            assert self.event is None
            assert self.forked is None
            self.event = self.stream.record_event()

        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        if self.stream is None:
            return

        assert self.event is not None

        if self.forked is not None:
            self.stream.wait_stream(self.forked)
            set_stream(self.stream)

        self.event = None
        self.forked = None

    def fork(self, priority: int | None = None) -> None:
        if self.stream is None:
            return

        assert self.event is not None

        if self.forked is not None:
            self.stream.wait_stream(self.forked)

        if priority is None:
            priority = self.stream.priority

        self.forked = Stream(self.stream.device, priority)
        set_stream(self.forked)
        self.event.wait()
