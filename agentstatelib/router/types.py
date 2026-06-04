from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from agentstatelib.core.patch import StatePatch

# Any async function that takes a context dict and returns a StatePatch
# is a valid agent. No inheritance required.
AgentFn = Callable[[dict[str, Any]], Awaitable["StatePatch"]]

# A function that takes the current state as a dict and returns True
# if this edge should be followed.
EdgeCondition = Callable[[dict[str, Any]], bool]
