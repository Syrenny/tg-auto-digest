# Research: Clean Architecture & TDD Refactor

**Date**: 2026-02-10
**Branch**: `002-clean-arch-tdd-refactor`

## R-001: Protocol File Location and Naming

**Decision**: Create a dedicated `src/telegram_radar/protocols.py`
file containing all Protocol definitions for the package.

**Rationale**: The project has a flat module structure (no sub-packages).
A single `protocols.py` matches the existing convention (`models.py`,
`settings.py`). Placing Protocols separately from consumers avoids
circular imports and keeps infrastructure modules decoupled. The name
`protocols.py` is more Pythonic than `interfaces.py` and signals
`typing.Protocol` usage.

**Alternatives considered**:
- `interfaces.py`: valid but carries Java/C# connotations.
- Co-located in `pipeline.py`: creates import coupling — infrastructure
  modules would need to import from their own consumer.
- One Protocol per file: over-engineering for ~3 Protocol classes.

## R-002: Structural Subtyping vs Explicit Inheritance

**Decision**: Infrastructure classes (`TelegramClientGateway`,
`LLMSummarizer`, `StateManager`) MUST NOT inherit from the Protocol.
Rely on structural subtyping (duck typing enforced by type checkers).

**Rationale**: The purpose of `typing.Protocol` is maximum decoupling.
Explicit inheritance would create an import dependency from
infrastructure back to `protocols.py`, partially defeating dependency
inversion. mypy already catches mismatches at call sites where
concrete objects are passed to Protocol-typed parameters.

**Alternatives considered**:
- Explicit inheritance for early mypy detection at class definition
  site: marginal benefit since the composition root (`__main__.py`)
  already exercises all typed call sites.
- ABCs with `@abstractmethod`: requires inheritance, loses structural
  subtyping. Rejected.

## R-003: `@runtime_checkable` Usage

**Decision**: Do NOT use `@runtime_checkable` on Protocol classes.

**Rationale**: `@runtime_checkable` only checks attribute name
existence, not method signatures, return types, or async status. It
has a documented performance penalty and known side-effect bugs with
`@property`. Static type checking is the correct enforcement
mechanism for this project.

**Alternatives considered**:
- Always `@runtime_checkable`: rejected due to shallow checks and
  performance penalty (CPython issue #102936).

## R-004: Async Methods in Protocols

**Decision**: Use `async def` in Protocol method signatures with
`...` (ellipsis) as the body. Match parameter names exactly between
Protocol and implementation.

**Rationale**: `async def` in a Protocol tells mypy the method returns
`Coroutine[Any, Any, T]`. Concrete `async def` implementations match
structurally. Parameter names must match (PEP 544 requirement) or
mypy will report incompatibility.

**Key gotchas**:
- Parameter names in Protocol MUST match implementing class names.
- Use `...` body (not `pass`) per PEP 544 convention.
- Cannot have `async @property`.

## R-005: Test Doubles for Protocol-Typed Parameters

**Decision**: Write concrete stub classes implementing the Protocol
for tests. Use `AsyncMock` only for behavioral verification (call
count/args), always with `spec=` parameter.

**Rationale**: Concrete stubs are type-checked by mypy — if a Protocol
method is added, a missing stub method causes a type error at the
call site. `AsyncMock` bypasses all type checking and returns
`AsyncMock` for any attribute access, masking Protocol drift. For 3-5
method Protocols, stubs are trivial to write.

**Alternatives considered**:
- `AsyncMock` everywhere: faster to write but no type safety.
- `AsyncMock(spec=ProtocolClass)`: known quirks with Protocol async
  method detection. Rejected as primary approach.
- `create_autospec`: similar issues with Protocols.

## R-006: pytest-asyncio Configuration

**Decision**: Use `asyncio_mode = "auto"` in `pyproject.toml`. Write
async test functions without explicit `@pytest.mark.asyncio` markers.

**Rationale**: The project is pure asyncio (no trio). Auto mode
eliminates boilerplate markers. pytest-asyncio 1.0+ (May 2025)
stabilized auto mode as the recommended configuration.

**Configuration**:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Alternatives considered**:
- `asyncio_mode = "strict"`: more verbose, useful for mixed-framework
  projects. Unnecessary here.

## R-007: State Encapsulation Pattern

**Decision**: Apply Command-Query Separation (CQS) to `StateManager`.
Add dedicated methods: `record_last_run(channels_parsed)`,
`get_channel_state(channel_id) -> ChannelState | None`, and make
`save()` accept no arguments (persists internal state).

**Rationale**: The current API forces callers to reach into `_state`
to mutate `last_run`, then pass the whole `AppState` back to `save()`.
CQS methods encapsulate mutations inside `StateManager`, making the
API predictable and testable. The pattern matches the existing
`get_last_message_id()` and `update_channel()` methods.

**Methods to add**:

| Current violation | Replacement |
|---|---|
| `state._state.last_run = LastRun(...)` + `state.save(state._state)` | `state.record_last_run(channels_parsed=...)` |
| `state._state.channels.get(str(ch.id))` | `state.get_channel_state(channel_id) -> ChannelState \| None` |
| `state.save(state._state)` | `state.save()` (no args, persists internal state) |

**Alternatives considered**:
- Make `_state` public: codifies broken encapsulation.
- Properties: `record_last_run()` has side effects (disk write) —
  a property setter would obscure this.
- Java-style getter/setter: anti-pattern in Python.
