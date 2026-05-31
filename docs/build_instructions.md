# agentstate — Week by Week Build Instructions

Every week has the same structure:
- **Files to work in** — exactly which files, in order
- **What to write in each file** — specific instructions, not code
- **How to test** — exact commands to run
- **How to know it worked** — what passing looks like

One rule: run the test commands at the end of every session, not just at the end of the week.

---

## Phase 0 · Pre-work · Before Week 1

### Files to create

**`pyproject.toml`** — already exists from `uv init`. Replace its contents entirely. Add `[build-system]` with hatchling, `[project]` with name, version `0.1.0`, description, `requires-python = ">=3.11"`, and `dependencies = ["pydantic>=2.0", "aiosqlite>=0.19"]`. Add `[project.optional-dependencies]` with `dev = ["pytest>=7.0", "pytest-asyncio>=0.21", "mypy>=1.0", "ruff>=0.1", "hypothesis>=6.0"]`. Add `[tool.ruff]` with `line-length = 88` and `target-version = "py312"`. Add `[tool.mypy]` with `python_version = "3.12"`, `strict = true`, `ignore_missing_imports = true`. Add `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` and `testpaths = ["tests"]`.

**`agentstate/__init__.py`** — write a single comment: `# Public API — exports added as modules are built`. Nothing else yet.

**`agentstate/core/__init__.py`** — empty file.

**`agentstate/router/__init__.py`** — empty file.

**`agentstate/coordination/__init__.py`** — empty file.

**`agentstate/memory/__init__.py`** — empty file.

**`agentstate/observability/__init__.py`** — empty file.

**`agentstate/api/__init__.py`** — empty file.

**`agentstate/contrib/__init__.py`** — empty file.

**`tests/__init__.py`** — empty file.

**`tests/conftest.py`** — write a single comment: `# Shared fixtures added here as tests are written`.

**`.gitignore`** — add entries for `.venv/`, `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `dist/`, `*.egg-info/`, `.env`, `*.db`, `.checkpoints/`.

**`.vscode/settings.json`** — set `python.defaultInterpreterPath` to `.venv/Scripts/python.exe`, `editor.formatOnSave` to true, `editor.defaultFormatter` to `charliermarsh.ruff`, `python.testing.pytestEnabled` to true, `python.testing.pytestArgs` to `["tests"]`.

### Commands to run

```powershell
# Install dependencies
uv add pydantic aiosqlite
uv add --dev pytest pytest-asyncio mypy ruff hypothesis

# Verify ruff runs clean on empty files
ruff check agentstate/

# Verify mypy runs clean on empty files
mypy agentstate/

# Verify pytest discovers tests folder without error
pytest tests/ -v

# Verify the package is importable
python -c "import agentstate; print('ok')"

# First commit
git add .
git commit -m "chore: initial scaffold"
git push -u origin main
```

### How to know it worked

All four commands exit with no errors. `pytest` says `no tests ran`. `python -c "import agentstate"` prints `ok` with no traceback.

---

## Phase 1 · Week 1 · SharedState · StateEvent · SQLiteStore

### Files to work in, in this order

1. `agentstate/core/state.py`
2. `agentstate/core/events.py`
3. `agentstate/memory/store.py`
4. `agentstate/memory/__init__.py`
5. `agentstate/core/__init__.py`
6. `tests/unit/test_state.py`
7. `tests/unit/test_events.py`
8. `tests/unit/test_store.py`

---

### `agentstate/core/state.py`

Import `BaseModel`, `Field` from `pydantic`. Import `Literal`, `Any` from `typing`. Import `uuid` and `time`.

Write a `WorkflowStatus` type alias using `Literal` with four values: `"running"`, `"complete"`, `"failed"`, `"paused"`.

Write a `Task` model with these fields: `id` as a string with a `default_factory` that calls `str(uuid.uuid4())`, `description` as a string, `status` as a `Literal` with values `"pending"`, `"running"`, `"done"`, `"failed"` defaulting to `"pending"`, `result` as `Any | None` defaulting to `None`, `created_at` as a float with `default_factory` calling `time.time()`, `updated_at` as a float with the same factory.

Write a `Goal` model with fields: `id` (uuid factory), `description` (str), `status` as `Literal["pending", "active", "complete", "failed"]` defaulting to `"pending"`, `created_at` (float, time factory).

Write an `Artifact` model with fields: `id` (uuid factory), `produced_by` (str — the agent_id that created it), `artifact_type` (str — examples: `"draft"`, `"source"`, `"summary"`, `"decision"`), `content` (`Any`), `created_at` (float, time factory).

Write a `Decision` model with fields: `id` (uuid factory), `made_by` (str), `description` (str), `rationale` (str), `timestamp` (float, time factory).

Write the main `SharedState` model with fields: `workflow_id` (str, uuid factory), `workflow_type` (str, default `"general"`), `goal` (str), `goals` (`dict[str, Goal]`, default empty dict using `default_factory=dict`), `tasks` (`dict[str, Task]`, default empty dict), `artifacts` (`dict[str, Artifact]`, default empty dict), `decisions` (`list[Decision]`, default empty list using `default_factory=list`), `facts` (`dict[str, Any]`, default empty dict), `status` (`WorkflowStatus`, default `"running"`), `created_at` (float, time factory), `updated_at` (float, time factory).

---

### `agentstate/core/events.py`

Import `BaseModel`, `Field` from `pydantic`. Import `Literal`, `Annotated`, `Union`, `Any` from `typing`. Import `uuid` and `time`.

Write a `BaseStateEvent` model with fields: `event_id` (str, uuid factory), `workflow_id` (str), `agent_id` (str), `timestamp` (float, time factory). This is the parent all events share.

Write six event subclasses, each inheriting from `BaseStateEvent`. For each one, add a `type` field typed as a `Literal` with a single string value, and set its default to that string. The six are:

`WorkflowStarted` — type is `"workflow_started"`. Extra fields: `workflow_type` (str), `goal` (str).

`WorkflowCompleted` — type is `"workflow_completed"`. Extra fields: `final_status` (str).

`PatchApplied` — type is `"patch_applied"`. Extra fields: `patch_id` (str), `target` (str), `old_value` (`Any`), `new_value` (`Any`), `reason` (str).

`ConflictDetected` — type is `"conflict_detected"`. Extra fields: `conflict_id` (str), `path` (str), `winner_agent_id` (str), `loser_agent_id` (str), `resolution_strategy` (str).

`CheckpointSaved` — type is `"checkpoint_saved"`. Extra fields: `checkpoint_id` (str), `event_count` (int).

`AgentErrored` — type is `"agent_errored"`. Extra fields: `error_type` (str), `error_message` (str), `retry_count` (int).

After all six classes, write a `StateEvent` type alias using `Annotated` and `Union` of all six types, with `Field(discriminator="type")`. This is the discriminated union — Pydantic will use the `type` field to decide which model to instantiate when deserializing.

Write a `TypeAdapter` for `StateEvent` at module level: `event_adapter = TypeAdapter(StateEvent)`. Import `TypeAdapter` from `pydantic`. This is how you deserialize a JSON string into the correct event subtype.

---

### `agentstate/memory/store.py`

Import `Protocol`, `runtime_checkable` from `typing`. Import `aiosqlite`. Import `json`. Import the `StateEvent` and `event_adapter` from `agentstate.core.events`. Import `BaseStateEvent` too.

Write the `StateStore` protocol. Decorate it with `@runtime_checkable`. It should have four async methods: `append(self, event: StateEvent) -> None`, `get_workflow(self, workflow_id: str) -> list[StateEvent]`, `since(self, workflow_id: str, index: int) -> list[StateEvent]`, `count(self, workflow_id: str) -> int`. Each method body is just `...`.

Write `InMemoryStore`. It has one instance variable `_events: dict[str, list[StateEvent]]` initialized to an empty dict in `__init__`. Implement all four methods. `append` adds to the list for that workflow_id, creating the list if needed. `get_workflow` returns a copy of the list for that workflow_id, or empty list. `since` returns the list sliced from index onward. `count` returns the length.

Write `SQLiteStore`. It takes a `path: str` parameter in `__init__`, stored as `self.path`. Write a private async method `_init_db(self, db)` that executes `CREATE TABLE IF NOT EXISTS events` with columns: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `event_id TEXT NOT NULL`, `workflow_id TEXT NOT NULL`, `type TEXT NOT NULL`, `data TEXT NOT NULL`, `timestamp REAL NOT NULL`. Then executes `CREATE INDEX IF NOT EXISTS idx_wf_id ON events(workflow_id)`. Then calls `await db.commit()`.

Implement `append`: open a connection with `async with aiosqlite.connect(self.path) as db`, call `await self._init_db(db)`, execute an INSERT with the five non-id fields, then `await db.commit()`. Serialize the event to JSON using `event.model_dump_json()`.

Implement `get_workflow`: open connection, call `_init_db`, execute `SELECT data FROM events WHERE workflow_id=? ORDER BY id ASC`, fetch all rows, return a list where each row's data is deserialized with `event_adapter.validate_json(row[0])`.

Implement `since`: same as `get_workflow` but add `LIMIT -1 OFFSET ?` with the index as the second parameter.

Implement `count`: execute `SELECT COUNT(*) FROM events WHERE workflow_id=?`, fetch one row, return the integer.

---

### `agentstate/memory/__init__.py`

Export `StateStore`, `InMemoryStore`, `SQLiteStore` from `agentstate.memory.store`. Set `__all__` explicitly.

---

### `agentstate/core/__init__.py`

Export `SharedState`, `Task`, `Goal`, `Artifact`, `Decision`, `WorkflowStatus` from `agentstate.core.state`. Export `StateEvent`, `BaseStateEvent`, `WorkflowStarted`, `WorkflowCompleted`, `PatchApplied`, `ConflictDetected`, `CheckpointSaved`, `AgentErrored`, `event_adapter` from `agentstate.core.events`. Set `__all__`.

---

### `tests/unit/test_state.py`

Write four test functions:

`test_shared_state_defaults` — create a `SharedState(goal="test goal")`, assert `workflow_id` is a non-empty string, assert `tasks` is an empty dict, assert `artifacts` is an empty dict, assert `status == "running"`.

`test_shared_state_validation_rejects_invalid_status` — import `ValidationError` from `pydantic`. Use `pytest.raises(ValidationError)` to assert that `SharedState(goal="x", status="invalid_status")` raises.

`test_task_defaults` — create a `Task(description="do something")`, assert `status == "pending"`, assert `result is None`, assert `id` is a non-empty string.

`test_two_states_have_different_ids` — create two `SharedState` objects with the same goal, assert their `workflow_id` values are different.

---

### `tests/unit/test_events.py`

Write five test functions:

`test_patch_applied_event_round_trip` — create a `PatchApplied` with all required fields. Call `.model_dump_json()` to get a JSON string. Call `event_adapter.validate_json(json_string)`. Assert the result is a `PatchApplied` instance. Assert `result.patch_id == original.patch_id`.

`test_discriminated_union_selects_correct_type` — create a `WorkflowStarted` event. Serialize it. Deserialize with `event_adapter.validate_json`. Assert the result is a `WorkflowStarted` instance, not a `PatchApplied`.

`test_all_event_types_serialize` — create one instance of each of the six event types. For each one, call `.model_dump_json()`, then `event_adapter.validate_json()` on the result. Assert no exceptions are raised and the round-trip preserves `event_id`.

`test_base_fields_present_on_all_events` — create one of each event type. For each, assert it has `event_id`, `workflow_id`, `agent_id`, `timestamp` attributes.

`test_invalid_type_field_raises` — use `pytest.raises(ValidationError)` to assert that `event_adapter.validate_json('{"type": "nonexistent", "workflow_id": "x", "agent_id": "y"}')` raises.

---

### `tests/unit/test_store.py`

Write a pytest fixture called `in_memory_store` that returns `InMemoryStore()`. Write a pytest fixture called `sqlite_store` that uses `tmp_path` (built-in pytest fixture) and returns `SQLiteStore(str(tmp_path / "test.db"))`.

Write these tests, each parametrized with `@pytest.mark.parametrize("store_fixture", ["in_memory_store", "sqlite_store"])` and using `request.getfixturevalue(store_fixture)` to get the store:

`test_append_and_retrieve` — create a `WorkflowStarted` event. `await store.append(event)`. `await store.get_workflow(event.workflow_id)`. Assert the list has length 1. Assert the first item's `event_id` equals the original.

`test_get_workflow_returns_empty_for_unknown_id` — `await store.get_workflow("does-not-exist")`. Assert the result is an empty list.

`test_count_increments_on_append` — append three events with the same `workflow_id`. Assert `await store.count(workflow_id)` equals 3.

`test_since_returns_from_index` — append four events to the same workflow. Assert `await store.since(workflow_id, 2)` returns a list of length 2 (the last two). Assert the items are the correct events.

`test_events_preserve_type_on_retrieve` — append a `PatchApplied` event. Retrieve it. Assert the retrieved event is a `PatchApplied` instance, not a base event.

Mark all tests that call async functions with `@pytest.mark.asyncio`.

---

### Test commands for Week 1

```powershell
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage to see what is tested
pytest tests/unit/ -v --tb=short

# Type check the new modules
mypy agentstate/core/ agentstate/memory/

# Check formatting
ruff check agentstate/core/ agentstate/memory/

# Quick smoke test — import the new code
python -c "from agentstate.core.state import SharedState; s = SharedState(goal='test'); print(s.workflow_id)"
python -c "from agentstate.memory.store import InMemoryStore, SQLiteStore; print('stores ok')"
```

### How to know it worked

All tests pass. Mypy reports no errors. The smoke test prints a UUID string and then `stores ok`.

---

## Phase 1 · Week 2 · StatePatch · AgentGraph · Publish v0.1

### Files to work in, in this order

1. `agentstate/core/patch.py`
2. `agentstate/router/types.py`
3. `agentstate/router/context.py`
4. `agentstate/router/graph.py`
5. `agentstate/router/__init__.py`
6. `agentstate/__init__.py`
7. `tests/unit/test_patch.py`
8. `tests/unit/test_context.py`
9. `tests/integration/test_graph_run.py`

---

### `agentstate/core/patch.py`

Import `BaseModel`, `Field` from `pydantic`. Import `Any` from `typing`. Import `uuid` and `time`.

Write `StatePatch` model with fields: `patch_id` (str, uuid factory), `agent_id` (str), `target` (str — a dotted path like `"tasks.task_1.status"`), `value` (`Any`), `reason` (str), `timestamp` (float, time factory), `priority` (int, default 0 — higher priority wins in priority-based conflict resolution).

Write `set_nested(obj: dict, path: str, value: Any) -> dict`. Split path on `"."`. Walk the dict one part at a time. For every part except the last, if that key does not exist in the current dict, set it to an empty dict, then step into it. For the last part, set the value. Return the original obj (modified in place is fine here). Never use `eval()` or `exec()`.

Write `get_nested(obj: dict, path: str) -> Any`. Split path on `"."`. Walk the dict one part at a time. If at any point the current thing is not a dict or the key does not exist, return `None`. Return the value at the final key.

Write `apply_patch(state: SharedState, patch: StatePatch) -> SharedState`. Import `SharedState` from `agentstate.core.state`. Call `state.model_dump()` to get a plain dict. Call `set_nested` on that dict with `patch.target` and `patch.value`. Call `SharedState.model_validate(modified_dict)` and return the result. The original `state` object must never be mutated — the function returns a brand new `SharedState`.

---

### `agentstate/router/types.py`

Import `Callable`, `Awaitable` from `typing`. Import `TYPE_CHECKING` from `typing`. If `TYPE_CHECKING`: import `StatePatch` from `agentstate.core.patch`.

Write the `AgentFn` type alias: `AgentFn = Callable[[dict], Awaitable["StatePatch"]]`. Add a docstring: `"Any async function that takes a context dict and returns a StatePatch is a valid agent. No inheritance required."`.

Write the `EdgeCondition` type alias: `EdgeCondition = Callable[[dict], bool]`. Add a docstring: `"A function that takes the current state as a dict and returns True if this edge should be followed."`.

---

### `agentstate/router/context.py`

Import `Any` from `typing`. Import `SharedState` from `agentstate.core.state`. Import `get_nested` from `agentstate.core.patch`.

Write `slice_state(state: SharedState, include_paths: list[str]) -> dict`. Convert state to a dict with `state.model_dump()`. Create an empty result dict. For each path in `include_paths`, call `get_nested(full_dict, path)`. If the value is not `None`, call `set_nested(result, path, value)` to place it at the same path in the result dict. Return the result dict. Import `set_nested` from `agentstate.core.patch`.

Edge case: if `include_paths` is empty, return the full state dict. This makes `slice_state(state, [])` behave like "give me everything" which is a safe default.

---

### `agentstate/router/graph.py`

Import `asyncio`. Import `Callable`, `Awaitable`, `Any` from `typing`. Import `dataclass` from `dataclasses`. Import `SharedState` from `agentstate.core.state`. Import `StatePatch`, `apply_patch` from `agentstate.core.patch`. Import `StateStore` from `agentstate.memory.store`. Import `InMemoryStore` from `agentstate.memory.store`. Import `slice_state` from `agentstate.router.context`. Import `AgentFn`, `EdgeCondition` from `agentstate.router.types`. Import `PatchApplied`, `WorkflowStarted`, `WorkflowCompleted` from `agentstate.core.events`.

Write a `_Node` dataclass with fields: `agent_id: str`, `fn: AgentFn`, `context_keys: list[str]`. Make it a frozen dataclass.

Write an `_Edge` dataclass with fields: `from_agent: str`, `to_agent: str`, `condition: EdgeCondition`. Make it a frozen dataclass.

Write the `AgentGraph` class.

`__init__` takes `store: StateStore | None = None` and `max_concurrent: int = 3`. Store `self._store = store or InMemoryStore()`. Store `self._nodes: dict[str, _Node] = {}`. Store `self._edges: list[_Edge] = []`. Store `self._sem = asyncio.Semaphore(max_concurrent)`.

Write the `node` method. It takes `agent_id: str` and `context: list[str] | None = None`. It returns a decorator. The decorator takes a function `fn: AgentFn`, creates a `_Node(agent_id=agent_id, fn=fn, context_keys=context or [])`, stores it in `self._nodes[agent_id]`, and returns `fn` unchanged. This is the `@graph.node("planner")` pattern.

Write the `edge` method. It takes `from_agent: str`, `to_agent: str`, and `condition: EdgeCondition = lambda s: True`. Creates and appends an `_Edge` to `self._edges`.

Write `_next_agent(self, current_id: str, state: SharedState) -> str | None`. Loops through `self._edges`. For each edge where `edge.from_agent == current_id`, call `edge.condition(state.model_dump())`. If the condition returns `True`, return `edge.to_agent`. If no matching edge fires, return `None`.

Write the `run` method as `async def run(self, state: SharedState, start: str, event_queue: asyncio.Queue | None = None) -> SharedState`. 

Inside `run`: append a `WorkflowStarted` event to the store. Set `current_id = start`. Enter a while loop that continues while `current_id is not None`. Inside the loop: get the node from `self._nodes[current_id]` — raise `KeyError` with a helpful message if not found. Call `slice_state(state, node.context_keys)` to get context dict. Use `async with self._sem:` to acquire the semaphore, then `await node.fn(context)` to get the patch. Call `apply_patch(state, patch)` and assign back to `state`. Create a `PatchApplied` event from the patch details. Append it to the store. If `event_queue` is not None, put the event into the queue with `event_queue.put_nowait(event)`. Call `self._next_agent(current_id, state)` and assign to `current_id`. After the loop, append a `WorkflowCompleted` event. Return `state`.

Handle the case where `start` is not in `self._nodes` — raise a `ValueError` with a clear message before the loop.

---

### `agentstate/router/__init__.py`

Export `AgentGraph` from `agentstate.router.graph`. Export `AgentFn`, `EdgeCondition` from `agentstate.router.types`. Export `slice_state` from `agentstate.router.context`. Set `__all__`.

---

### `agentstate/__init__.py`

This is your public API. Import and re-export everything users need:

From `agentstate.core.state`: `SharedState`, `Task`, `Goal`, `Artifact`, `Decision`.

From `agentstate.core.patch`: `StatePatch`, `apply_patch`, `set_nested`, `get_nested`.

From `agentstate.core.events`: `StateEvent`, `PatchApplied`, `WorkflowStarted`, `WorkflowCompleted`, `ConflictDetected`, `AgentErrored`.

From `agentstate.router.graph`: `AgentGraph`.

From `agentstate.router.types`: `AgentFn`, `EdgeCondition`.

From `agentstate.router.context`: `slice_state`.

From `agentstate.memory.store`: `StateStore`, `InMemoryStore`, `SQLiteStore`.

Set `__version__ = "0.1.0"`. Set `__all__` to a list of all the above names.

---

### `tests/unit/test_patch.py`

Write six test functions:

`test_set_nested_simple` — call `set_nested({}, "a", "value")`, assert result is `{"a": "value"}`.

`test_set_nested_deep_path` — call `set_nested({}, "a.b.c", 42)`, assert `result["a"]["b"]["c"] == 42`.

`test_set_nested_creates_intermediate_dicts` — call `set_nested({}, "tasks.task_1.status", "done")`, assert no `KeyError` is raised and the value is set correctly.

`test_get_nested_returns_none_for_missing_path` — call `get_nested({}, "a.b.c")`, assert result is `None`. No exception should be raised.

`test_apply_patch_returns_new_state` — create a `SharedState(goal="test")`. Create a `StatePatch(agent_id="a", target="facts.key", value="val", reason="test")`. Call `apply_patch(state, patch)`. Assert the returned object is a different Python object (`is not` check). Assert the original state's `facts` dict is still empty. Assert the new state's facts has the key.

`test_apply_patch_deep_target` — create a `SharedState(goal="test")`. Apply a patch with target `"tasks.t1.status"` and value `"done"`. Assert `new_state.tasks["t1"]["status"] == "done"`.

---

### `tests/unit/test_context.py`

Write three test functions:

`test_slice_state_returns_only_requested_paths` — create a `SharedState` with a goal and one fact. Call `slice_state(state, ["goal"])`. Assert the result contains `"goal"` but does not contain `"tasks"` or `"artifacts"`.

`test_slice_state_handles_nested_paths` — create a `SharedState(goal="test")`. Apply a patch to add `facts.key1 = "value1"` and `facts.key2 = "value2"`. Call `slice_state(state, ["facts.key1"])`. Assert `result["facts"]["key1"] == "value1"`. Assert `"key2"` is not in `result.get("facts", {})`.

`test_slice_state_empty_include_returns_full_state` — create a `SharedState(goal="test")`. Call `slice_state(state, [])`. Assert the result contains `"goal"` and `"tasks"` and `"artifacts"`.

---

### `tests/integration/test_graph_run.py`

Write three integration tests. These use real `AgentGraph` with stub agent functions — no LLM calls.

`test_single_agent_workflow` — define an async function `stub_agent(context: dict) -> StatePatch` that returns a `StatePatch` with target `"facts.done"`, value `True`, reason `"test"`. Create an `AgentGraph()`. Register the agent with `@graph.node("agent_a")`. Do not add any edges. Create a `SharedState(goal="test")`. Call `await graph.run(state, start="agent_a")`. Assert `final_state.facts.get("done") == True`.

`test_two_agent_pipeline_in_order` — define two stub agents. First returns a patch setting `"facts.step"` to `1`. Second returns a patch setting `"facts.step"` to `2`. Add an edge from first to second with condition `lambda s: s.get("facts", {}).get("step") == 1`. Run the graph starting at first agent. Assert final `facts["step"] == 2`.

`test_graph_raises_on_unknown_start_agent` — create an empty `AgentGraph`. Use `pytest.raises(ValueError)` to assert that `await graph.run(SharedState(goal="x"), start="nonexistent")` raises a `ValueError`.

---

### Test commands for Week 2

```powershell
# Run all tests
pytest tests/ -v

# Run only integration tests
pytest tests/integration/ -v

# Type check everything built so far
mypy agentstate/

# Check for formatting issues
ruff check agentstate/

# Full smoke test — the decorator pattern
python -c "
import asyncio
from agentstate import SharedState, AgentGraph, StatePatch

graph = AgentGraph()

@graph.node('planner', context=['goal'])
async def planner(context):
    return StatePatch(agent_id='planner', target='facts.planned', value=True, reason='test')

async def main():
    state = SharedState(goal='test goal')
    result = await graph.run(state, start='planner')
    print('facts:', result.facts)
    assert result.facts.get('planned') == True
    print('ok')

asyncio.run(main())
"

# Build the package
python -m build

# Test install from local dist
pip install dist/agentstate-0.1.0-py3-none-any.whl --force-reinstall
python -c "import agentstate; print(agentstate.__version__)"
```

### Publish commands

```powershell
# Install twine if not installed
pip install twine

# Upload to test PyPI first
twine upload --repository testpypi dist/*

# Verify it installs from test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ agentstate

# Upload to real PyPI
twine upload dist/*

# Tag the release
git tag v0.1.0
git push origin v0.1.0
```

### How to know it worked

All tests pass. `mypy agentstate/` exits with no errors. The smoke test prints `facts: {'planned': True}` and then `ok`. The package installs and `agentstate.__version__` prints `0.1.0`.

---

## Phase 2 · Week 3 · ContextSlice · Conflict Detection · InvariantValidator

### Files to work in, in this order

1. `agentstate/coordination/conflicts.py`
2. `agentstate/coordination/invariants.py`
3. `agentstate/router/graph.py` (modify existing)
4. `agentstate/coordination/__init__.py`
5. `agentstate/__init__.py` (update exports)
6. `tests/unit/test_conflicts.py`
7. `tests/unit/test_invariants.py`
8. `tests/integration/test_conflict_flow.py`

---

### `agentstate/coordination/conflicts.py`

Import `Protocol`, `runtime_checkable` from `typing`. Import `BaseModel`, `Field` from `pydantic`. Import `uuid`, `time`. Import `StatePatch` from `agentstate.core.patch`.

Write `ConflictRecord` model with fields: `conflict_id` (str, uuid factory), `path` (str), `existing_patch` (`StatePatch`), `incoming_patch` (`StatePatch`), `winner_agent_id` (str), `loser_agent_id` (str), `resolution_strategy` (str), `resolved_at` (float, time factory).

Write the `ConflictResolver` protocol. Decorate with `@runtime_checkable`. One method: `resolve(self, existing: StatePatch, incoming: StatePatch) -> StatePatch`. Body is `...`. Add a docstring explaining the contract: takes two conflicting patches, returns the one that should be applied.

Write `LastWriteWins` class implementing `ConflictResolver`. `resolve` returns whichever patch has the larger `timestamp`. If equal, return `incoming`.

Write `PriorityBased` class implementing `ConflictResolver`. `resolve` returns whichever patch has the larger `priority`. If equal, fall back to last-write-wins.

Write `RejectIncoming` class implementing `ConflictResolver`. `resolve` always returns `existing`. Add a docstring: "Always keeps the first patch received. Incoming patch is logged but not applied."

Write `ConflictDetector` class. `__init__` takes `resolver: ConflictResolver`. Stores `self.resolver = resolver`. Stores `self._pending: dict[str, StatePatch] = {}` (path to patch mapping). Stores `self._conflicts: list[ConflictRecord] = []`.

Write `submit(self, patch: StatePatch) -> StatePatch`. If `patch.target` is already in `_pending`, there is a conflict. Call `self.resolver.resolve(existing, incoming)`. Determine winner and loser. Create a `ConflictRecord`. Append to `self._conflicts`. Update `self._pending[patch.target]` to the winner. Return the winner. If no conflict, store in `_pending` and return the patch unchanged.

Write `drain(self) -> list[StatePatch]`. Returns all values from `_pending` as a list. Clears `_pending`. Does not clear `_conflicts`.

Write `conflicts` as a property returning a copy of `self._conflicts`.

Write `reset(self)`. Clears both `_pending` and `_conflicts`. Call this at the start of each agent call cycle.

---

### `agentstate/coordination/invariants.py`

Import `Protocol`, `runtime_checkable` from `typing`. Import `BaseModel`, `Field` from `pydantic`. Import `SharedState` from `agentstate.core.state`.

Write `InvariantViolation` model with fields: `rule_name` (str), `description` (str), `severity` as `Literal["warning", "error"]` defaulting to `"error"`.

Write the `InvariantChecker` protocol. Decorate with `@runtime_checkable`. One method: `check(self, state: SharedState) -> list[InvariantViolation]`. Body is `...`.

Write `TasksReferenceExistingGoals` class implementing `InvariantChecker`. `check` iterates all tasks. For each task, if `task.get("goal_id")` (tasks may be dicts or `Task` objects depending on how state was set — handle both) is not in `state.goals`, append a violation. Returns list of violations found.

Write `CompletedGoalsHaveNoBlockingTasks` class implementing `InvariantChecker`. `check` finds all goals with status `"complete"`. For each, checks if any task has `goal_id` matching and status `"pending"` or `"running"`. If yes, appends a violation. Returns list.

Write `check_all(state: SharedState, checkers: list[InvariantChecker]) -> list[InvariantViolation]`. Calls each checker. Collects and returns all violations from all checkers.

---

### `agentstate/router/graph.py` (modifications)

Add import of `ConflictDetector`, `ConflictRecord` from `agentstate.coordination.conflicts`. Add import of `InvariantChecker`, `InvariantViolation`, `check_all` from `agentstate.coordination.invariants`. Add import of `ConflictDetected` from `agentstate.core.events`.

Modify `__init__` to accept `conflict_resolver: ConflictResolver | None = None` and `invariant_checkers: list[InvariantChecker] | None = None`. Import `ConflictResolver` and `LastWriteWins` from `agentstate.coordination.conflicts`. Store `self._conflict_detector = ConflictDetector(conflict_resolver or LastWriteWins())`. Store `self._invariant_checkers: list[InvariantChecker] = invariant_checkers or []`.

Add method `add_invariant(self, checker: InvariantChecker) -> None` that appends to `self._invariant_checkers`.

Modify the `run` method. Before the while loop, call `self._conflict_detector.reset()`. Inside the loop, after getting the patch from the agent, call `self._conflict_detector.submit(patch)` and use the returned patch (which is the winner). After applying the patch, call `check_all(state, self._invariant_checkers)`. If any violations with severity `"error"` are found, raise a `RuntimeError` with the violation descriptions. After calling `_conflict_detector.submit`, check `self._conflict_detector.conflicts` — if any new conflicts were added since the last check, create a `ConflictDetected` event and append it to the store.

---

### `agentstate/coordination/__init__.py`

Export `ConflictResolver`, `ConflictDetector`, `ConflictRecord`, `LastWriteWins`, `PriorityBased`, `RejectIncoming` from `agentstate.coordination.conflicts`. Export `InvariantChecker`, `InvariantViolation`, `check_all`, `TasksReferenceExistingGoals`, `CompletedGoalsHaveNoBlockingTasks` from `agentstate.coordination.invariants`. Set `__all__`.

---

### `agentstate/__init__.py` (update)

Add imports from `agentstate.coordination`: `ConflictResolver`, `LastWriteWins`, `PriorityBased`, `RejectIncoming`, `InvariantChecker`, `InvariantViolation`. Update `__all__`.

---

### `tests/unit/test_conflicts.py`

Write six test functions:

`test_no_conflict_when_different_paths` — create a detector with `LastWriteWins()`. Submit two patches with different targets. Assert `len(detector.conflicts) == 0`.

`test_conflict_detected_on_same_path` — submit two patches with the same target. Assert `len(detector.conflicts) == 1`.

`test_last_write_wins_returns_newer` — create two patches with same target. Set first timestamp to `1000.0`, second to `2000.0`. Submit both. Drain patches. Assert the winning patch has agent_id of the second patch.

`test_priority_based_returns_higher_priority` — create two patches with same target. Set first `priority=1`, second `priority=10`. Use `PriorityBased()` resolver. Submit both. Assert winner is the second patch.

`test_reject_incoming_keeps_first` — use `RejectIncoming()`. Submit two patches to same target. Assert winner is the first patch.

`test_drain_clears_pending` — submit two patches to different targets. Call `drain()`. Assert returned list has length 2. Assert `drain()` again returns empty list.

---

### `tests/unit/test_invariants.py`

Write four test functions:

`test_no_violations_on_clean_state` — create a `SharedState(goal="test")`. Run `check_all(state, [TasksReferenceExistingGoals()])`. Assert result is an empty list.

`test_detects_task_with_missing_goal` — create a `SharedState(goal="test")`. Use `apply_patch` to add a task with `goal_id = "nonexistent_goal_id"`. Run `check_all(state, [TasksReferenceExistingGoals()])`. Assert result has at least one violation.

`test_custom_invariant_checker` — write an inline class implementing `InvariantChecker` that always returns one violation. Verify `check_all` includes that violation.

`test_multiple_checkers_all_run` — create a state that violates both built-in checkers. Assert `check_all(state, [TasksReferenceExistingGoals(), CompletedGoalsHaveNoBlockingTasks()])` returns at least two violations.

---

### `tests/integration/test_conflict_flow.py`

Write two tests:

`test_conflict_detected_and_logged_in_store` — create a graph with two agents. Both agents return patches targeting the same path with different values. Run the graph. Retrieve events from the store. Assert at least one `ConflictDetected` event exists in the log.

`test_invariant_violation_halts_workflow` — add an invariant checker that always raises. Use `pytest.raises(RuntimeError)` to assert the graph run raises.

---

### Test commands for Week 3

```powershell
pytest tests/ -v

mypy agentstate/

ruff check agentstate/

# Test conflict resolution manually
python -c "
from agentstate.coordination.conflicts import ConflictDetector, LastWriteWins, PriorityBased
from agentstate import StatePatch

detector = ConflictDetector(LastWriteWins())
p1 = StatePatch(agent_id='agent_a', target='tasks.t1.status', value='done', reason='r1')
p2 = StatePatch(agent_id='agent_b', target='tasks.t1.status', value='failed', reason='r2')
w1 = detector.submit(p1)
w2 = detector.submit(p2)
print('conflicts:', len(detector.conflicts))
patches = detector.drain()
print('winner:', patches[0].agent_id)
"
```

---

## Phase 2 · Week 4 · FastAPI HTTP Layer · v0.2

### Files to work in, in this order

1. `agentstate/api/app.py`
2. `agentstate/api/auth.py`
3. `agentstate/api/routes.py`
4. `agentstate/api/streaming.py`
5. `agentstate/api/__init__.py`
6. `tests/integration/test_api.py`

Install FastAPI first:

```powershell
uv add --optional api fastapi "uvicorn[standard]"
pip install "agentstate[api]"
```

---

### `agentstate/api/app.py`

Import `FastAPI` from `fastapi`. Import `SQLiteStore` from `agentstate.memory.store`.

Write `create_app(db_path: str = "agentstate.db") -> FastAPI`. Inside: create a `FastAPI` instance with `title="agentstate API"` and `version="0.2.0"`. Create a `SQLiteStore(db_path)` instance. Store it on the app using `app.state.store = store`. Import and include the router from `agentstate.api.routes` with prefix `"/v1"`. Return the app.

Write a module-level `app = create_app()` for direct `uvicorn` invocation.

---

### `agentstate/api/auth.py`

Import `Header`, `HTTPException` from `fastapi`. Import `os`.

Write `verify_api_key(x_api_key: str = Header(...)) -> str`. Get valid keys from `os.environ.get("AGENTSTATE_API_KEYS", "dev-key-123")`. Split on comma. Strip whitespace from each. If `x_api_key` is not in the set of valid keys, raise `HTTPException(status_code=401, detail={"error_code": "invalid_api_key", "message": "Invalid or missing API key"})`. Return the key.

---

### `agentstate/api/routes.py`

Import `APIRouter`, `HTTPException`, `Depends`, `Request` from `fastapi`. Import `StreamingResponse` from `fastapi.responses`. Import `SharedState` from `agentstate.core.state`. Import `StatePatch` from `agentstate.core.patch`. Import `StateStore` from `agentstate.memory.store`. Import `verify_api_key` from `agentstate.api.auth`. Import `asyncio`, `json`.

Write a helper `get_store(request: Request) -> StateStore` that returns `request.app.state.store`. This is the dependency injection pattern.

Write `POST /workflows` endpoint. Accepts a request body with `goal: str` and `workflow_type: str = "general"`. Creates a `SharedState`. Appends a `WorkflowStarted` event to the store. Returns the state with status code 201.

Write `GET /workflows/{workflow_id}` endpoint. Retrieves all events for the workflow. If empty, raise `HTTPException(404)`. Replay events to reconstruct current state. Return the state.

Write `POST /workflows/{workflow_id}/patches` endpoint. Accepts a `StatePatch` in the request body. Gets events to verify the workflow exists (404 if not). Appends a `PatchApplied` event to the store. Returns the reconstructed state.

Write `GET /workflows/{workflow_id}/events` endpoint. Returns a `StreamingResponse` with `media_type="text/event-stream"`. The generator function: gets all events, yields each as `f"data: {event.model_dump_json()}\n\n"`. Include a `retry: 3000\n\n` line at the start to tell clients to retry after 3 seconds if disconnected.

Write `GET /health` endpoint. Returns `{"status": "ok", "version": "0.2.0"}`. No auth required on this one.

All endpoints except `/health` should use `Depends(verify_api_key)`.

---

### `agentstate/api/streaming.py`

This file holds a helper for future real-time streaming (not full polling like the route above). Write `create_event_stream(store: StateStore, workflow_id: str, poll_interval: float = 0.5)` as an async generator. It yields events and checks for new ones every `poll_interval` seconds. Keep a `last_count` variable. In a loop: get events `since(workflow_id, last_count)`. For each new event, yield `f"data: {event.model_dump_json()}\n\n"`. Update `last_count`. `await asyncio.sleep(poll_interval)`. Stop after 300 iterations (5 minutes max).

---

### `agentstate/api/__init__.py`

Export `create_app` from `agentstate.api.app`. Set `__all__`.

---

### `tests/integration/test_api.py`

Install `httpx` for TestClient:

```powershell
uv add --dev httpx
```

Import `TestClient` from `fastapi.testclient`. Import `create_app` from `agentstate.api`.

Write a fixture `client` that creates `TestClient(create_app(db_path=":memory:"))`. Note: `:memory:` for SQLite means in-memory database, reset each test. However, `aiosqlite` requires careful handling with `:memory:` — if this causes issues, use `tmp_path` and a real file path instead.

Write four tests:

`test_health_check` — `GET /health`. Assert status 200. Assert `response.json()["status"] == "ok"`.

`test_create_workflow_requires_auth` — `POST /v1/workflows` with no headers. Assert status 401.

`test_create_and_retrieve_workflow` — POST to create, use `x-api-key: dev-key-123` header. Assert 201. Take the `workflow_id`. GET the workflow. Assert 200 and matching `workflow_id`.

`test_submit_patch_updates_state` — create a workflow. Submit a patch with target `"facts.test"` and value `"hello"`. Retrieve the workflow. Assert `response.json()["facts"]["test"] == "hello"`.

---

### Test and run commands for Week 4

```powershell
# Run all tests
pytest tests/ -v

# Start the API server locally
uvicorn agentstate.api.app:app --reload

# In another terminal, test the API manually
curl -X POST http://localhost:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-key-123" \
  -d "{\"goal\": \"test workflow\", \"workflow_type\": \"research\"}"

# Open the auto-generated docs
# Navigate to http://localhost:8000/docs in your browser

# Build and publish v0.2.0
python -m build
twine upload dist/*
git tag v0.2.0
git push origin v0.2.0
```

---

## Phase 3 · Week 5 · StateStore Protocol · PostgreSQL · Checkpoint

### Files to work in, in this order

1. `agentstate/memory/store.py` (refactor)
2. `agentstate/memory/checkpoint.py`
3. `agentstate/memory/__init__.py` (update)
4. `agentstate/__init__.py` (update)
5. `tests/unit/test_store.py` (add PostgreSQL tests)
6. `tests/integration/test_checkpoint_recovery.py`

---

### `agentstate/memory/store.py` (refactor)

The `StateStore` Protocol and `InMemoryStore` stay the same. Refactor `SQLiteStore` to wrap every write in an explicit transaction. Change the `append` method: after opening the connection, call `async with db.execute("BEGIN")` — actually with aiosqlite you handle this by ensuring `db.isolation_level` is set correctly or by using `await db.execute("BEGIN")` explicitly before your INSERT, then `await db.commit()`. Add a docstring to the class explaining it is one of two built-in implementations of `StateStore` and that any class satisfying the `StateStore` protocol works with `AgentGraph`.

Add a `PostgreSQLStore` stub class. At the top of the file, write `try: import asyncpg; HAS_ASYNCPG = True` and `except ImportError: HAS_ASYNCPG = False`. Write the class with a docstring: "PostgreSQL implementation of StateStore. Install with: uv add asyncpg". In `__init__`, raise `ImportError("asyncpg required: uv add asyncpg")` if `HAS_ASYNCPG` is False. Accept `dsn: str` parameter (example: `"postgresql://user:pass@localhost/agentstate"`). Implement `_init_pool` as an async method that creates an `asyncpg` connection pool. Implement all four `StateStore` methods using the pool. Add an `async def close(self)` method that closes the pool.

The SQL schema for PostgreSQL differs slightly from SQLite — use `SERIAL PRIMARY KEY` instead of `INTEGER PRIMARY KEY AUTOINCREMENT`, and `TEXT` for all string fields. The rest is the same.

---

### `agentstate/memory/checkpoint.py`

Import `BaseModel`, `Field` from `pydantic`. Import `uuid`, `time`. Import `Path` from `pathlib`. Import `SharedState` from `agentstate.core.state`. Import `StateStore` from `agentstate.memory.store`.

Write `Checkpoint` model with fields: `checkpoint_id` (str, uuid factory), `workflow_id` (str), `state` (`SharedState`), `event_count` (int), `created_at` (float, time factory).

Write `async def save_checkpoint(state: SharedState, store: StateStore, directory: str = ".checkpoints") -> Checkpoint`. Create `Path(directory)` and call `.mkdir(exist_ok=True, parents=True)`. Get `event_count = await store.count(state.workflow_id)`. Create a `Checkpoint` instance. Write it to a file named `{workflow_id}_{checkpoint_id}.json` using `path.write_text(checkpoint.model_dump_json())`. Return the checkpoint.

Write `def load_latest_checkpoint(workflow_id: str, directory: str = ".checkpoints") -> Checkpoint | None`. Get `Path(directory)`. Call `.glob(f"{workflow_id}_*.json")`. If no files found, return `None`. Sort by modification time (`.stat().st_mtime`). Return `Checkpoint.model_validate_json(latest_file.read_text())`.

Write `def load_checkpoint(checkpoint_id: str, directory: str = ".checkpoints") -> Checkpoint`. Search for file matching `f"*_{checkpoint_id}.json"`. If not found, raise `FileNotFoundError(f"Checkpoint {checkpoint_id} not found in {directory}")`. Load and return.

Modify `AgentGraph.run()` to accept `start_from_checkpoint: Checkpoint | None = None`. If provided, set `state = checkpoint.state` at the beginning and replay only events since `checkpoint.event_count` (the store already has the old events, you just skip re-running the agents that already ran — but you need to figure out which agent to start from based on the checkpoint state).

---

### `tests/integration/test_checkpoint_recovery.py`

Write three tests:

`test_save_and_load_checkpoint` — create a `SharedState`. Create a store. Apply some patches. Call `await save_checkpoint(state, store)`. Call `load_latest_checkpoint(state.workflow_id)`. Assert the loaded checkpoint's `state.workflow_id == state.workflow_id`.

`test_checkpoint_preserves_full_state` — create a state with non-empty facts and tasks via patches. Save checkpoint. Load it. Assert facts and tasks in loaded state match original.

`test_workflow_resumes_from_checkpoint` — define a graph with three agents. Save a checkpoint after the first agent runs (this requires manually calling `save_checkpoint` inside the test after a partial run). Create a new `AgentGraph` with the same store. Run starting from the checkpoint. Assert the final state includes artifacts from all three agents. This test verifies that loading a checkpoint and continuing produces the same result as an uninterrupted run.

---

### Test commands for Week 5

```powershell
pytest tests/ -v

# Test checkpoint manually
python -c "
import asyncio
from agentstate import SharedState, AgentGraph, StatePatch
from agentstate.memory.store import SQLiteStore
from agentstate.memory.checkpoint import save_checkpoint, load_latest_checkpoint

async def main():
    store = SQLiteStore('test_ckpt.db')
    state = SharedState(goal='checkpoint test')

    graph = AgentGraph(store=store)

    @graph.node('agent_a')
    async def agent_a(ctx):
        return StatePatch(agent_id='agent_a', target='facts.step', value=1, reason='step 1')

    state = await graph.run(state, start='agent_a')
    cp = await save_checkpoint(state, store)
    print('saved checkpoint:', cp.checkpoint_id)

    loaded = load_latest_checkpoint(state.workflow_id)
    print('loaded workflow_id:', loaded.state.workflow_id)
    print('loaded facts:', loaded.state.facts)

asyncio.run(main())
"

# Clean up test files
Remove-Item test_ckpt.db -ErrorAction SilentlyContinue
Remove-Item -Recurse .checkpoints -ErrorAction SilentlyContinue
```

---

## Phase 3 · Week 6 · ReplayDebugger · WorkflowAnalysis · v0.3

### Files to work in, in this order

1. `agentstate/memory/replay.py`
2. `agentstate/observability/analysis.py`
3. `agentstate/__init__.py` (update)
4. `tests/unit/test_replay.py` (update)
5. `tests/unit/test_analysis.py` (new file)

---

### `agentstate/memory/replay.py`

Import `SharedState` from `agentstate.core.state`. Import `StatePatch`, `apply_patch`, `set_nested` from `agentstate.core.patch`. Import `StateEvent`, `PatchApplied` from `agentstate.core.events`.

Write `replay(events: list[StateEvent]) -> SharedState`. Create a base `SharedState` — you need a starting point, so scan events for a `WorkflowStarted` event to get `workflow_id`, `goal`, and `workflow_type`. Apply all `PatchApplied` events in order using `apply_patch`. Return the final state. If no `WorkflowStarted` event exists, raise `ValueError("Cannot replay: no WorkflowStarted event found")`.

Write the `ReplayDebugger` class. `__init__` takes `events: list[StateEvent]`. Sort events by timestamp ascending. Store as `self._events`. Initialize `self._cursor = 0`.

Write `step(self) -> tuple[StateEvent, SharedState]`. If `self._cursor >= len(self._events)`, raise `StopIteration("No more events to replay")`. Advance cursor. Return the event at the new cursor position and `replay(self._events[:self._cursor])`.

Write `jump_to(self, index: int) -> SharedState`. Validate index is within bounds. Set `self._cursor = index`. Return `replay(self._events[:index])`.

Write `state_at(self, timestamp: float) -> SharedState`. Filter events to those with `timestamp <= target_timestamp`. Return `replay(filtered_events)`.

Write `reset(self) -> None`. Sets `self._cursor = 0`.

Write `current_index` as a property returning `self._cursor`.

Write `total_events` as a property returning `len(self._events)`.

---

### `agentstate/observability/analysis.py`

Import `BaseModel`, `Field` from `pydantic`. Import `Any` from `typing`. Import `StateEvent`, `PatchApplied`, `ConflictDetected`, `AgentErrored`, `WorkflowStarted`, `WorkflowCompleted` from `agentstate.core.events`.

Write `AnomalyFlag` model with fields: `rule_name` (str), `description` (str), `severity` as `Literal["warning", "error"]` defaulting to `"warning"`.

Write `AgentStats` model with fields: `agent_id` (str), `patch_count` (int, default 0), `error_count` (int, default 0), `total_duration_seconds` (float, default 0.0).

Write `WorkflowSummary` model with fields: `workflow_id` (str), `total_duration_seconds` (float), `agent_stats` (`dict[str, AgentStats]`, default empty dict), `conflict_count` (int, default 0), `conflict_rate` (float, default 0.0 — conflicts divided by total patches), `total_patches` (int, default 0), `total_errors` (int, default 0), `is_anomalous` (bool, default False), `anomaly_flags` (`list[AnomalyFlag]`, default empty list).

Write `analyze_workflow(events: list[StateEvent]) -> WorkflowSummary`. Compute all the stats by iterating events once. Find `WorkflowStarted` and `WorkflowCompleted` to get duration. For each `PatchApplied`, increment the agent's patch count. For each `ConflictDetected`, increment conflict count. For each `AgentErrored`, increment the agent's error count. Compute `conflict_rate`. Run anomaly rules: flag if `conflict_rate > 0.2`, flag if any agent has `error_count > 3`, flag if `total_duration_seconds > 300`. Set `is_anomalous = True` if any error-severity flags exist. Return the summary.

---

### `tests/unit/test_replay.py` (additions)

Add these tests to the existing file:

`test_replay_reconstructs_state_from_events` — create a `WorkflowStarted` event and three `PatchApplied` events. Call `replay(events)`. Assert the final state has all three patches applied.

`test_debugger_step_advances_cursor` — create a `ReplayDebugger` with 3 events. Call `step()` twice. Assert `debugger.current_index == 2`.

`test_debugger_jump_to_specific_index` — create debugger with 5 events. Call `jump_to(3)`. Assert state reflects first 3 events only.

`test_debugger_state_at_timestamp` — create events with explicit timestamps 1.0, 2.0, 3.0. Call `state_at(1.5)`. Assert only the first event is reflected.

`test_debugger_raises_stop_iteration_at_end` — create debugger with 1 event. Call `step()` once. Use `pytest.raises(StopIteration)` to assert second `step()` raises.

---

### Test and publish commands for Week 6

```powershell
pytest tests/ -v

mypy agentstate/

# Test replay manually
python -c "
import asyncio, time
from agentstate import SharedState, AgentGraph, StatePatch
from agentstate.memory.store import InMemoryStore
from agentstate.memory.replay import ReplayDebugger, replay
from agentstate.core.events import WorkflowStarted, PatchApplied

async def main():
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    @graph.node('a')
    async def agent_a(ctx):
        return StatePatch(agent_id='a', target='facts.x', value=1, reason='set x')

    @graph.node('b')
    async def agent_b(ctx):
        return StatePatch(agent_id='b', target='facts.y', value=2, reason='set y')

    graph.edge('a', 'b')

    state = SharedState(goal='replay test')
    final = await graph.run(state, start='a')
    
    events = await store.get_workflow(final.workflow_id)
    print(f'Total events: {len(events)}')
    
    debugger = ReplayDebugger(events)
    while True:
        try:
            event, state_at_step = debugger.step()
            print(f'Step {debugger.current_index}: {event.type} -> facts: {state_at_step.facts}')
        except StopIteration:
            break

asyncio.run(main())
"

# Publish v0.3.0
python -m build
twine upload dist/*
git tag v0.3.0
git push origin v0.3.0
```

---

## Phase 4 · Week 7 · OpenTelemetry Instrumentation · Jaeger

### Files to work in, in this order

1. `agentstate/observability/tracing.py`
2. `agentstate/router/graph.py` (add instrumentation)
3. `tests/unit/test_tracing.py` (new file)

Install OTel:

```powershell
uv add --optional otel opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc
```

Start Jaeger (requires Docker):

```powershell
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
```

---

### `agentstate/observability/tracing.py`

Write all OTel imports inside a `try/except ImportError` block that sets `HAS_OTEL = True/False`. This way the library works even if opentelemetry is not installed.

Write `setup_tracing(service_name: str = "agentstate", exporter_endpoint: str = "http://localhost:4317") -> None`. If `HAS_OTEL` is False, raise `ImportError("Install opentelemetry: pip install agentstate[otel]")`. Create a `TracerProvider`. Create an `OTLPSpanExporter` with the given endpoint and `insecure=True`. Add a `BatchSpanProcessor`. Call `trace.set_tracer_provider(provider)`. Store the tracer on a module-level variable.

Write `get_tracer() -> Any`. If OTel not available or not set up, return a no-op tracer (a simple object whose `start_as_current_span` is a no-op context manager). If available, return `trace.get_tracer("agentstate")`.

Write a `_noop_span` context manager class that implements `__enter__` (returns self) and `__exit__` (does nothing) and has a `set_attribute` method that does nothing. This is returned by the no-op tracer so instrumented code does not need to check if OTel is active.

Write `NoOpTracer` class with `start_as_current_span(name, **kwargs)` method that returns a `_noop_span()` instance.

---

### `agentstate/router/graph.py` (add instrumentation)

Import `get_tracer` from `agentstate.observability.tracing`.

In the `run` method, wrap the entire method body in `with get_tracer().start_as_current_span("workflow.run") as workflow_span:`. Set attributes: `workflow_span.set_attribute("workflow.id", state.workflow_id)`, `workflow_span.set_attribute("workflow.type", state.workflow_type)`.

Inside the while loop, wrap each agent call in `with get_tracer().start_as_current_span(f"agent.{current_id}") as agent_span:`. Set attributes before the call: `agent_span.set_attribute("agent.id", current_id)`. After the call: `agent_span.set_attribute("agent.patch_target", patch.target)`, `agent_span.set_attribute("agent.patch_reason", patch.reason)`. In a try/except around the agent call, catch all exceptions, call `agent_span.record_exception(e)`, set `agent_span.set_attribute("agent.success", False)`, then re-raise. If successful, set `agent_span.set_attribute("agent.success", True)`.

---

### `tests/unit/test_tracing.py`

Write three tests:

`test_tracing_import_does_not_crash_without_otel` — call `from agentstate.observability.tracing import get_tracer`. Call `get_tracer()`. Assert no exception is raised even if opentelemetry is not installed.

`test_noop_tracer_context_manager_works` — get a no-op tracer. Use it as `with tracer.start_as_current_span("test") as span:`. Call `span.set_attribute("key", "value")`. Assert no exception.

`test_graph_runs_without_tracing_setup` — run a simple one-agent graph without calling `setup_tracing`. Assert the graph runs normally and returns correct state. Instrumentation should be invisible when OTel is not configured.

---

### Test and verify commands for Week 7

```powershell
pytest tests/ -v

# Run a workflow and check Jaeger
python -c "
import asyncio
from agentstate.observability.tracing import setup_tracing
from agentstate import SharedState, AgentGraph, StatePatch
from agentstate.memory.store import InMemoryStore

setup_tracing(service_name='agentstate-test')

async def main():
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    @graph.node('planner')
    async def planner(ctx):
        return StatePatch(agent_id='planner', target='facts.plan', value='research topic', reason='planned')

    @graph.node('researcher')
    async def researcher(ctx):
        return StatePatch(agent_id='researcher', target='artifacts.sources', value=['source1'], reason='researched')

    graph.edge('planner', 'researcher', lambda s: 'plan' in s.get('facts', {}))

    state = SharedState(goal='Test OTel tracing')
    final = await graph.run(state, start='planner')
    print('Workflow complete:', final.facts)
    print('Check Jaeger at http://localhost:16686')

asyncio.run(main())
"

# Open Jaeger in browser
start http://localhost:16686
# Select service: agentstate-test
# Find your trace and inspect the spans
```

---

## Phase 4 · Week 8 · Rich Dashboard · v0.4

### Files to work in, in this order

1. `agentstate/observability/dashboard.py`
2. `agentstate/router/graph.py` (add event_queue support — already partially done)
3. `agentstate/observability/__init__.py`
4. `tests/unit/test_dashboard.py` (new file)

Install rich:

```powershell
uv add --optional dashboard rich
```

---

### `agentstate/observability/dashboard.py`

Write all rich imports inside a `try/except ImportError` block setting `HAS_RICH = True/False`.

Write `WorkflowDashboard` class. `__init__` takes `event_queue: asyncio.Queue`. Store it. Initialize `self._events: list[StateEvent] = []`. Initialize `self._start_time = time.time()`. Initialize `self._current_agent: str = "waiting..."`.

Write `_build_table(self) -> Any` (returns a rich `Table`). Create a table with columns: `Time`, `Agent`, `Event Type`, `Target`. Add the last 10 events from `self._events`. For each event, format the timestamp as seconds since start. Return the table.

Write `_build_layout(self) -> Any` (returns a rich renderable). Create a `rich.panel.Panel` containing: a header line showing `"Workflow Dashboard"`, a spinner with current agent name, the events table, a footer showing conflict count, artifact count, and elapsed time. Use `rich.table.Table` for the main structure and nest a panel inside.

Write `async def run(self) -> None`. If `HAS_RICH` is False, raise `ImportError`. Create a `rich.live.Live` instance with `refresh_per_second=4`. Enter `async with live:` loop. In the loop: try `event = await asyncio.wait_for(self._event_queue.get(), timeout=0.25)`. If the event is the sentinel value `None`, break. Append to `self._events`. Update `self._current_agent` if it is a `PatchApplied` event. Call `live.update(self._build_layout())`. On `asyncio.TimeoutError`, just call `live.update(self._build_layout())` and continue.

Write `stop(self) -> None`. Puts `None` into the queue as a sentinel to end the run loop.

---

### `agentstate/observability/__init__.py`

Export `WorkflowDashboard` from `agentstate.observability.dashboard`. Export `setup_tracing`, `get_tracer` from `agentstate.observability.tracing`. Export `WorkflowSummary`, `analyze_workflow`, `AnomalyFlag` from `agentstate.observability.analysis`. Set `__all__`.

---

### `tests/unit/test_dashboard.py`

Write three tests:

`test_dashboard_import_does_not_crash_without_rich` — import `WorkflowDashboard`. Assert no error.

`test_dashboard_receives_events_from_queue` — create an `asyncio.Queue`. Create a `WorkflowDashboard(queue)`. Put two fake events into the queue. Put `None` as sentinel. Run `asyncio.run(dashboard.run())` — it should complete without error (no actual terminal rendering in tests, mock rich.Live if needed using `unittest.mock.patch`).

`test_graph_puts_events_in_queue` — create a graph and an `asyncio.Queue`. Run the graph with `event_queue=queue`. Assert the queue is not empty after the run. Assert each item is a `StateEvent` instance.

---

### Test and publish commands for Week 8

```powershell
pytest tests/ -v

# Demo the dashboard — run this in a real terminal (not VS Code integrated terminal for best rendering)
python -c "
import asyncio
from agentstate import SharedState, AgentGraph, StatePatch
from agentstate.memory.store import InMemoryStore
from agentstate.observability.dashboard import WorkflowDashboard

async def main():
    queue = asyncio.Queue()
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    @graph.node('planner')
    async def planner(ctx):
        await asyncio.sleep(0.5)  # simulate thinking
        return StatePatch(agent_id='planner', target='facts.plan', value='done', reason='planned')

    @graph.node('researcher')
    async def researcher(ctx):
        await asyncio.sleep(1.0)
        return StatePatch(agent_id='researcher', target='artifacts.sources', value=['s1','s2'], reason='found sources')

    @graph.node('writer')
    async def writer(ctx):
        await asyncio.sleep(0.8)
        return StatePatch(agent_id='writer', target='artifacts.draft', value='draft text', reason='wrote draft')

    graph.edge('planner', 'researcher', lambda s: 'plan' in s.get('facts', {}))
    graph.edge('researcher', 'writer', lambda s: bool(s.get('artifacts', {}).get('sources')))

    dashboard = WorkflowDashboard(queue)
    state = SharedState(goal='Demo workflow')

    results = await asyncio.gather(
        graph.run(state, start='planner', event_queue=queue),
        dashboard.run()
    )
    final_state = results[0]
    print('Final artifacts:', list(final_state.artifacts.keys()))

asyncio.run(main())
"

# Take a screenshot of the terminal output and add to README

# Publish v0.4.0
python -m build
twine upload dist/*
git tag v0.4.0
git push origin v0.4.0
```

---

## Phase 5 · Week 9 · Testing Properly · Docker

### Files to work in, in this order

1. `tests/conftest.py` (populate shared fixtures)
2. `tests/property/test_patch_properties.py`
3. `tests/property/test_replay_properties.py`
4. `tests/property/test_invariant_properties.py`
5. `Dockerfile`
6. `docker-compose.yml`

Install hypothesis:

```powershell
uv add --dev hypothesis
```

---

### `tests/conftest.py`

Write shared fixtures used across multiple test files:

`sample_workflow_id` fixture — returns a fixed UUID string `"test-workflow-00000000-0000-0000-0000-000000000001"`.

`sample_state` fixture — returns `SharedState(goal="test goal", workflow_id="test-workflow-00000000-0000-0000-0000-000000000001")`.

`in_memory_store` fixture — returns `InMemoryStore()`.

`sqlite_store` fixture with `tmp_path` — returns `SQLiteStore(str(tmp_path / "test.db"))`.

`sample_patch` fixture — returns `StatePatch(agent_id="test_agent", target="facts.test", value="test_value", reason="test reason")`.

`populated_store` async fixture — creates an `InMemoryStore`. Creates a state. Creates and appends a `WorkflowStarted`, two `PatchApplied`, and one `WorkflowCompleted` event. Returns `(store, state.workflow_id)`.

---

### `tests/property/test_patch_properties.py`

Import `given`, `strategies as st` from `hypothesis`. Import `assume` from `hypothesis`.

Write `test_set_nested_roundtrip`. Use `@given(st.lists(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))), min_size=1, max_size=5), st.integers())`. Inside: join the list with `"."` to make a path. Call `set_nested({}, path, value)`. Call `get_nested(result, path)`. Assert `get_nested_result == value`. Use `assume` to skip if any path part is empty.

Write `test_apply_patch_never_mutates_original`. Use `@given(st.text(min_size=1), st.text(min_size=1), st.integers())`. Generate a goal string and target string and value. Create a `SharedState(goal=goal)`. Create a `StatePatch`. Call `apply_patch(state, patch)`. Assert original `state.model_dump()` has not changed.

Write `test_apply_patch_always_returns_shared_state`. Use the same strategy. Assert the return type of `apply_patch` is always `SharedState`.

Write `test_set_nested_with_many_paths_does_not_raise`. Use `@given(st.lists(st.from_regex(r'[a-z][a-z0-9_]{0,9}', fullmatch=True), min_size=1, max_size=8))`. Build a path and set a value. Assert no exception.

---

### `tests/property/test_replay_properties.py`

Write `test_replay_is_deterministic`. Use `@given(st.integers(min_value=1, max_value=10))`. Generate N patches as `PatchApplied` events with `target = f"facts.key_{i}"`. Add a `WorkflowStarted` event at the beginning. Call `replay(events)` twice. Assert both calls return states with equal `model_dump()` outputs.

Write `test_replay_subset_has_fewer_facts`. Use a fixed set of 5 events. Assert `len(replay(events[:3]).facts) <= len(replay(events).facts)`. This verifies replay is monotonically accumulating.

---

### `tests/property/test_invariant_properties.py`

Write `test_empty_state_has_no_violations`. Use `@given(st.text(min_size=1))`. Create `SharedState(goal=goal_text)`. Assert `check_all(state, [TasksReferenceExistingGoals()])` is an empty list.

Write `test_adding_task_with_valid_goal_has_no_violations`. Generate a goal ID and task. Add both to state via patches. Assert no invariant violations.

---

### `Dockerfile`

Write a multi-stage Dockerfile. First stage named `builder`: use `FROM python:3.12-slim AS builder`. Set `WORKDIR /app`. Copy `pyproject.toml` and `README.md`. Install uv: `RUN pip install uv`. Run `RUN uv pip install --system ".[api,otel,dashboard]"`. Copy the rest of the source.

Second stage named `runtime`: use `FROM python:3.12-slim AS runtime`. Set `WORKDIR /app`. Copy the installed Python packages from builder: `COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12`. Copy the application code: `COPY --from=builder /app/agentstate ./agentstate`. Set `EXPOSE 8000`. Set environment variable `AGENTSTATE_API_KEYS=dev-key-123` as a default (users override in production). Set `CMD ["uvicorn", "agentstate.api.app:app", "--host", "0.0.0.0", "--port", "8000"]`.

---

### `docker-compose.yml`

Write a compose file with three services:

`api` service: `build: .`, ports `"8000:8000"`, environment `AGENTSTATE_API_KEYS: dev-key-123`, `depends_on: [redis, jaeger]`.

`redis` service: `image: redis:alpine`, ports `"6379:6379"`.

`jaeger` service: `image: jaegertracing/all-in-one:latest`, ports `"16686:16686"` and `"4317:4317"`.

---

### Test commands for Week 9

```powershell
# Run all tests including property tests
pytest tests/ -v

# Run property tests specifically with more examples
pytest tests/property/ -v --hypothesis-seed=0

# Run property tests and show statistics
pytest tests/property/ -v --hypothesis-show-statistics

# Build and test Docker image
docker build -t agentstate:latest .
docker run -p 8000:8000 agentstate:latest

# Test the containerized API
curl http://localhost:8000/health

# Run full compose stack
docker-compose up -d

# Verify all services are running
docker-compose ps

# Test the full stack
curl -X POST http://localhost:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-key-123" \
  -d "{\"goal\": \"docker test\"}"

# Stop compose stack
docker-compose down
```

---

## Phase 5 · Week 10 · API Hardening · Auth · Caching · v0.5

### Files to work in, in this order

1. `agentstate/api/cache.py`
2. `agentstate/api/auth.py` (update with rate limiting)
3. `agentstate/api/app.py` (update with cache and rate limiter)
4. `agentstate/api/routes.py` (update with cache integration)
5. `tests/integration/test_api.py` (add cache and auth tests)

Install Redis client:

```powershell
uv add redis
```

Start Redis if not running via docker-compose:

```powershell
docker run -d --name redis -p 6379:6379 redis:alpine
```

---

### `agentstate/api/cache.py`

Write all imports inside a `try/except ImportError` for redis. Set `HAS_REDIS`.

Write `StatePatchCache` class. `__init__` takes `redis_url: str = "redis://localhost:6379"` and `default_ttl: int = 3600`. If `HAS_REDIS` is False, raise `ImportError`. Create an async Redis client using `redis.asyncio.from_url(redis_url)`.

Write `_cache_key(self, agent_id: str, context: dict) -> str`. Import `hashlib`, `json`. Create a string `f"{agent_id}:{json.dumps(context, sort_keys=True, default=str)}"`. Return `"agentstate:patch:" + hashlib.sha256(content.encode()).hexdigest()`.

Write `async def get(self, agent_id: str, context: dict) -> StatePatch | None`. Build cache key. Call `await self._redis.get(key)`. If `None`, return `None`. Deserialize with `StatePatch.model_validate_json(value)` and return.

Write `async def set(self, agent_id: str, context: dict, patch: StatePatch, ttl: int | None = None) -> None`. Build cache key. Serialize patch with `.model_dump_json()`. Call `await self._redis.setex(key, ttl or self.default_ttl, serialized)`.

Write `async def close(self) -> None`. Calls `await self._redis.aclose()`.

---

### `agentstate/api/auth.py` (update)

Add a `RateLimiter` class. `__init__` takes `redis_url: str`, `max_requests: int = 100`, `window_seconds: int = 60`. Creates a Redis client.

Write `async def check(self, api_key: str) -> bool`. Build key `f"agentstate:ratelimit:{api_key}"`. Call `await redis.incr(key)`. If the value is 1 (first request in window), call `await redis.expire(key, self.window_seconds)`. If the value exceeds `max_requests`, return `False`. Return `True`.

Update `verify_api_key` to be a class or factory that optionally includes rate limiting. If a `RateLimiter` is provided, check it and raise `HTTPException(429, {"error_code": "rate_limit_exceeded", "message": "Too many requests"})` if the check fails.

---

### `tests/integration/test_api.py` (additions)

Add tests:

`test_rate_limiter_returns_429_after_limit` — this requires a real Redis connection, so mark with `@pytest.mark.skipif(not redis_available, reason="Redis not available")`. Send requests in a loop until you hit the limit. Assert 429 is returned.

`test_cache_returns_same_patch_on_second_call` — this is tested at the cache class level, not the API level. Create a `StatePatchCache`. Store a patch. Retrieve it. Assert retrieved patch equals stored patch.

`test_health_endpoint_does_not_require_auth` — GET `/health` with no headers. Assert 200.

---

### Test and publish commands for Week 10

```powershell
pytest tests/ -v

# Run API server with Redis caching
$env:AGENTSTATE_API_KEYS="dev-key-123"
uvicorn agentstate.api.app:app --reload

# Test rate limiting (sends 5 requests)
for ($i=1; $i -le 5; $i++) {
    curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
    Write-Host ""
}

# Publish v0.5.0
python -m build
twine upload dist/*
git tag v0.5.0
git push origin v0.5.0
```

---

## Phase 6 · Week 11 · API Audit · Protocols Everywhere · Type Stubs · ADRs

### Files to work in, in this order

1. `agentstate/__init__.pyi` (new — type stub)
2. `agentstate/router/graph.pyi` (new — type stub)
3. `docs/decisions/ADR-001-event-sourcing.md`
4. `docs/decisions/ADR-002-protocol-over-abc.md`
5. `docs/decisions/ADR-003-patch-immutability.md`
6. `docs/decisions/ADR-004-agentfn-callable.md`
7. Every existing module — docstring and API audit pass

---

### `agentstate/__init__.pyi`

A `.pyi` stub file contains type signatures only — no implementations. Write it as Python type annotations. Import all the types you export. For each class, write `class ClassName: ...`. For each function, write `def function_name(param: type) -> return_type: ...`. For `__version__`, write `__version__: str`. For `__all__`, write `__all__: list[str]`. This file tells mypy and IDEs exactly what your package exports without them having to execute any code.

---

### `agentstate/router/graph.pyi`

Write stubs for `AgentGraph`. Include `__init__`, `node`, `edge`, `add_invariant`, and `run` with full type signatures. The `node` method returns a decorator — the stub should reflect this with a `Callable` return type.

---

### ADR files

Each ADR follows this exact structure:

```
# ADR-00N: Title

## Status
Accepted

## Context
[2–3 paragraphs explaining the problem you were facing and the options you considered]

## Decision
[1–2 paragraphs stating what you decided]

## Consequences
### Positive
[bullet list of what you gained]

### Negative
[bullet list of what you gave up or complications this introduces]

### Neutral
[bullet list of things that are just different, neither good nor bad]
```

**ADR-001-event-sourcing.md** — Context: you needed to persist workflow state and wanted auditability and recovery. Options were: store current state only (simple but no history), store event log (complex but auditable), or both. Decision: store events only, derive state via replay. Consequences: free audit trail and recovery, but replay can be slow for very long workflows (mitigated by checkpoints).

**ADR-002-protocol-over-abc.md** — Context: you needed a `StateStore` interface so users could provide their own persistence backends. Options were: abstract base class (requires inheritance), Protocol (structural typing, no inheritance). Decision: Protocol. Consequences: users can implement any class without importing from your library, but they lose explicit interface documentation that ABCs provide via IDE tools.

**ADR-003-patch-immutability.md** — Context: you needed agents to update state. Options were: agents mutate state directly, agents return a mutation descriptor (StatePatch). Decision: StatePatch returned from agents, applied by the library. Consequences: full attribution and logging of every change, but adds a layer of indirection.

**ADR-004-agentfn-callable.md** — Context: you needed to define what an "agent" is. Options were: require subclassing a base class (tight coupling), require implementing a Protocol (structural), define as a plain callable type. Decision: `AgentFn = Callable[[dict], Awaitable[StatePatch]]`. Consequences: any async function works, any model provider works, no library import required to be a valid agent, but less IDE support for the interface compared to a base class.

---

### API audit pass — every module

Go through every public function and class. For each one, write a one-sentence docstring if it does not have one. The test: can a developer understand what this does without reading the implementation? If the answer is no after reading the docstring, the function is either doing too much or is poorly named.

---

### Test commands for Week 11

```powershell
# Run mypy in strict mode — fix every error before moving on
mypy agentstate/ --strict

# Check stub files are valid
python -m mypy agentstate/__init__.pyi

# Run all tests
pytest tests/ -v

# Check that the stubs are used by mypy correctly
python -c "
# Create a temporary test file
import tempfile, os
test_code = '''
import agentstate
reveal_type(agentstate.SharedState)
reveal_type(agentstate.AgentGraph)
'''
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(test_code)
    fname = f.name
os.system(f'mypy {fname}')
os.unlink(fname)
"
```

---

## Phase 6 · Week 12 · Packaging · CI/CD · Integrations · v1.0-alpha

### Files to work in, in this order

1. `pyproject.toml` (finalize optional deps)
2. `.github/workflows/test.yml`
3. `.github/workflows/publish.yml`
4. `examples/integrations/langchain_adapter.py`
5. `examples/integrations/langgraph_adapter.py`
6. `examples/integrations/litellm_agent.py`
7. `CHANGELOG.md`
8. `README.md` (final version)

---

### `pyproject.toml` (finalize)

Add all optional dependency groups: `api`, `otel`, `dashboard`, `contrib`, `dev`. Make sure `contrib = []` (empty — the base agent helper has no extra deps). Add `[project.urls]` with `Homepage`, `Repository`, `Documentation` URLs. Add `[project.scripts]` with `agentstate = "agentstate.cli:main"` if you want a CLI entry point. Add classifiers including development status `"3 - Alpha"`.

---

### `.github/workflows/test.yml`

Write a workflow that triggers on `push` to `main` and on `pull_request`. Uses `ubuntu-latest`. Steps: checkout, set up Python 3.12, install uv, run `uv pip install --system ".[dev]"`, run `ruff check agentstate/`, run `mypy agentstate/ --strict`, run `pytest tests/ -v`.

---

### `.github/workflows/publish.yml`

Write a workflow that triggers on `push` to tags matching `v*`. Uses `ubuntu-latest`. Steps: checkout, set up Python 3.12, install build and twine (`pip install build twine`), run `python -m build`, run `twine upload dist/*` using `${{ secrets.PYPI_TOKEN }}` as the password and `__token__` as the username.

Add the `PYPI_TOKEN` secret: go to pypi.org → Account Settings → API Tokens → create a token scoped to your `agentstate` project. In GitHub: repo Settings → Secrets → Actions → New repository secret, name it `PYPI_TOKEN`.

---

### `examples/integrations/langchain_adapter.py`

Write a module with a docstring explaining: this file shows how to use agentstate alongside LangChain. agentstate does not import LangChain. This is a user-space bridge.

Write a function `make_agentstate_agent(chain: Any, agent_id: str, target: str) -> AgentFn`. It returns an async function that calls `chain.invoke(context)` (or `await chain.ainvoke(context)` for async chains), takes the string result, and wraps it in a `StatePatch(agent_id=agent_id, target=target, value=result, reason="LangChain chain output")`. This is the entire adapter — one function, no inheritance.

---

### `examples/integrations/litellm_agent.py`

Write a factory function `make_litellm_agent(agent_id: str, model: str, target: str, system_prompt: str) -> AgentFn`. It returns an async function. Inside: import `litellm` (only inside the function to avoid hard dependency). Call `await litellm.acompletion(model=model, messages=[...])`. Parse the JSON response into a `StatePatch`. Include the retry-with-correction pattern. Return the `StatePatch`.

---

### `CHANGELOG.md`

Write changelog entries for each version: v0.1.0 (initial release), v0.2.0 (conflict detection, FastAPI), v0.3.0 (replay debugger, checkpoint), v0.4.0 (OTel, dashboard), v0.5.0 (production hardening), v1.0.0-alpha (API stabilization, ADRs, type stubs).

---

### Publish commands for Week 12

```powershell
# Update version in pyproject.toml to 1.0.0-alpha
# Then build and tag
python -m build

# Tag triggers the publish workflow
git add .
git commit -m "chore: v1.0.0-alpha release"
git tag v1.0.0-alpha
git push origin main
git push origin v1.0.0-alpha

# Watch the GitHub Actions workflow in your browser
start https://github.com/yourusername/agentstate/actions
```

---

## Phase 7 · Weeks 13–14 · Write and Ship

### Week 13 — Files to create

1. `docs/design.md`
2. `examples/workflows/research_pipeline.py` (annotated)
3. `examples/workflows/support_ticket.py` (annotated)

### `docs/design.md`

Structure: Problem Statement (what breaks without a coordination layer), Architecture Overview (SharedState → StatePatch → AgentGraph → StateStore → Event Log), Key Design Decisions (one section per ADR expanded into prose), Comparison Table (agentstate vs LangGraph vs CrewAI vs AutoGen — be honest), Known Limitations, Future Directions.

Length: 1500–2000 words. Write it in plain prose, not bullet lists. The reader is a developer deciding whether to use your library.

### Example notebooks

`research_pipeline.py` — planner, researcher, writer. Every line of library code has a comment explaining why it is written that way. Under 80 lines of actual library code (comments do not count). Uses stub agents that return hardcoded patches — the point is to demonstrate the library API, not a real LLM integration.

`support_ticket.py` — different state shape: customer message, priority, category, escalation history. Shows that the same library handles a completely different workflow type without any changes.

---

### Week 14 — Files to create

1. `blog_post_1_draft.md` (in repo root, will be posted externally)
2. `blog_post_2_draft.md`

### `blog_post_1_draft.md`

Title: "What happens between LLM calls — why I built agentstate"

Structure: open with the insight (the hard part of multi-agent systems is not the models, it is the coordination between them), describe a specific failure mode you would solve, explain your architecture in three paragraphs, show the decorator example in 15 lines, present the benchmark data from local model reliability work, close with where to find the library.

### `blog_post_2_draft.md`

Title: "How I would scale agentstate to 100,000 workflows per day"

Structure: current architecture and where it breaks, SQLite → PostgreSQL transition, single process → worker pool, in-process agent execution → Redis task queue, what to instrument first, what the architecture looks like after three iterations. No code. Pure architectural thinking in plain prose.

---

### Final publish commands for Week 14

```powershell
# Update version to 1.0.0
# Edit pyproject.toml: version = "1.0.0"
# Edit agentstate/__init__.py: __version__ = "1.0.0"

python -m build
git add .
git commit -m "release: v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0

# Post to dev.to (manual — go to dev.to and paste blog post content)
# Post Show HN (manual — go to news.ycombinator.com/submit)

# Verify final package
pip install agentstate==1.0.0
python -c "import agentstate; print(agentstate.__version__)"
```

---

## Quick Reference — Commands You Run Every Session

```powershell
# Before writing any code
.venv\Scripts\activate

# After writing code
ruff check agentstate/        # catch style issues immediately
mypy agentstate/              # catch type errors immediately
pytest tests/ -v              # run all tests

# Before committing
ruff check agentstate/
mypy agentstate/ --strict
pytest tests/ -v --tb=short
git add .
git commit -m "type: description"

# Commit message prefixes:
# feat: new feature
# fix: bug fix
# refactor: code change with no behavior change
# test: adding tests
# docs: documentation
# chore: tooling, config, dependencies
```