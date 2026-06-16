from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentstatelib.core.patch import StatePatch

# Any async function that accepts a context dict and returns a StatePatch
# (or a list of StatePatch for agents that produce multiple patches per turn)
# is a valid agent. No inheritance required.
AgentFn = Callable[[dict[str, Any]], Awaitable["StatePatch | list[StatePatch]"]]

# A function that takes the current state as a dict and returns True
# if this edge should be followed.
EdgeCondition = Callable[[dict[str, object]], bool]
