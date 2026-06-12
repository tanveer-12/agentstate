from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentstatelib.core.patch import StatePatch
    from agentstatelib.router.context import ContextSlice

# Any async function that takes a context dict and returns a StatePatch
# is a valid agent. No inheritance required.
AgentFn = Callable[["ContextSlice"], Awaitable[list["StatePatch"]]]

# A function that takes the current state as a dict and returns True
# if this edge should be followed.
EdgeCondition = Callable[[dict[str, object]], bool]
