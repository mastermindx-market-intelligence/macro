"""Provider-neutral execution-adapter contract for Executive OS workers.

The first implementation is the existing attested Codex CLI adapter.  Future
Qwen, GLM, xAI, ACP, or cloud implementations plug into this interface; they do
not get their own queue, lease model, or lifecycle database.

The protocol names the operations the current supervisor and broker require,
including ``status()`` as a construction-time launch precondition.  Optional
receipts (launch attestation, UID sweep, cleanup) remain feature-detected by
the supervisor and can become required by a provider's acceptance policy
without weakening this common floor.
"""
from __future__ import annotations

import dataclasses
import importlib
import weakref
from typing import Protocol, Sequence, runtime_checkable

from control_plane.worker_execution_contract import (
    CancelReceipt,
    CollectionReceipt,
    ProcessInspector,
    ValidationReceipt,
    WorkerLaunchSpec,
    WorkerRecoveryBinding,
    WorkerProcessRef,
    WorkerRunStatus,
)


ADAPTER_INTERFACE_VERSION = "mastermind.worker_adapter/v1"
_CONSTRUCTED_REVIEWED_ADAPTERS: weakref.WeakSet[object] = weakref.WeakSet()


class AdapterBindingError(ValueError):
    """Reviewed adapter identity or required capability failed to bind."""


@dataclasses.dataclass(frozen=True)
class AdapterDescriptor:
    """Non-secret facts about one reviewed execution interface."""

    adapter_id: str
    interface_version: str = ADAPTER_INTERFACE_VERSION
    structured_output: bool = True
    implemented: bool = False
    implementation: str | None = None


ADAPTER_DESCRIPTORS: dict[str, AdapterDescriptor] = {
    # The retained facade exists; its concrete qualified host backend is not
    # installed. Catalogue source must not imply worker admission.
    "attended-fabric": AdapterDescriptor(
        adapter_id="attended-fabric",
        implemented=False,
        implementation="control_plane.executive_fabric_adapter.AttendedFabricWorkerAdapter",
    ),
    "codex-cli": AdapterDescriptor(
        adapter_id="codex-cli",
        implemented=True,
        implementation="control_plane.codex_worker.CodexWorkerAdapter",
    ),
    "claude-compatible-subscription": AdapterDescriptor(
        adapter_id="claude-compatible-subscription",
        implementation=(
            "control_plane.claude_subscription_worker"
            ".ClaudeSubscriptionWorkerAdapter"
        ),
    ),
    "claude-code": AdapterDescriptor(
        adapter_id="claude-code",
        implemented=False,
        implementation="control_plane.claude_worker.ClaudeCodeWorkerAdapter",
    ),
    # Clean, deliberately unarmed seams for later provider work.  A routing
    # policy cannot bind a live worker through an unimplemented descriptor.
    "openai-compatible": AdapterDescriptor(
        adapter_id="openai-compatible", implemented=False
    ),
    "acp": AdapterDescriptor(adapter_id="acp", implemented=False),
}


def adapter_descriptor(adapter_id: str) -> AdapterDescriptor:
    """Resolve a reviewed adapter id or fail closed."""

    resolved = str(adapter_id).strip().lower()
    try:
        return ADAPTER_DESCRIPTORS[resolved]
    except KeyError as exc:
        raise ValueError(f"unknown worker adapter {adapter_id!r}") from exc


def adapter_implementation(adapter_id: str) -> type:
    """Resolve a reviewed descriptor to its implementation class."""

    descriptor = adapter_descriptor(adapter_id)
    if not descriptor.implementation:
        raise AdapterBindingError(f"worker adapter {adapter_id!r} is not implemented")
    module_name, _, class_name = descriptor.implementation.rpartition(".")
    try:
        module = importlib.import_module(module_name)
        implementation = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        raise AdapterBindingError(
            f"worker adapter {descriptor.adapter_id!r} implementation is not importable"
        ) from exc
    if not isinstance(implementation, type):
        raise AdapterBindingError(
            f"worker adapter {descriptor.adapter_id!r} implementation is not a class"
        )
    identity = getattr(implementation, "adapter_id", None)
    if identity != descriptor.adapter_id:
        raise AdapterBindingError(
            f"implementation identity {identity!r} does not match descriptor "
            f"{descriptor.adapter_id!r}"
        )
    return implementation


def _implementation_adapter_id(adapter: object) -> str:
    """Read the immutable identity from the implementation, never a caller label."""

    adapter_type = type(adapter)
    try:
        class_value = getattr(adapter_type, "adapter_id", None)
        if isinstance(class_value, str) and class_value.strip():
            return class_value.strip()
        if isinstance(class_value, property):
            value = class_value.__get__(adapter, adapter_type)
            if isinstance(value, str) and value.strip():
                return value.strip()
    except AdapterBindingError:
        raise
    except Exception as exc:
        raise AdapterBindingError(
            f"{adapter_type.__name__} adapter_id is not readable"
        ) from exc
    raise AdapterBindingError(
        f"{adapter_type.__name__} does not expose an immutable adapter_id"
    )


def _require_status(adapter: object) -> object:
    """Read status at bind time; attribute-access failures stay in-family."""

    try:
        return getattr(adapter, "status", None)
    except Exception as exc:
        raise AdapterBindingError(
            f"{type(adapter).__name__} status is not readable"
        ) from exc


def _is_caller_supplied_adapter(
    value: object, implementation: type, adapter_id: str
) -> bool:
    """True when a value is already an adapter instance, not a constructor argument."""

    if isinstance(value, (str, bytes, type)):
        return False
    value_type = type(value)
    try:
        if value_type is implementation or issubclass(value_type, implementation):
            return True
    except TypeError:
        return False
    return getattr(value_type, "adapter_id", None) == adapter_id and callable(
        getattr(value, "status", None)
    )


def _codex_constructed_adapters() -> object:
    from control_plane.codex_worker import _CONSTRUCTED_CODEX_ADAPTERS

    return _CONSTRUCTED_CODEX_ADAPTERS


def construct_reviewed_adapter(adapter_id: str, *args: object, **kwargs: object) -> object:
    """Construct the reviewed implementation. Never accepts a caller-supplied instance."""

    implementation = adapter_implementation(adapter_id)
    for value in (*args, *kwargs.values()):
        if _is_caller_supplied_adapter(value, implementation, adapter_id):
            raise AdapterBindingError(
                "construct_reviewed_adapter does not accept a caller-supplied adapter"
            )
    adapter = implementation(*args, **kwargs)
    _CONSTRUCTED_REVIEWED_ADAPTERS.add(adapter)
    return adapter


def bind_reviewed_adapter(adapter: object, adapter_id: str) -> AdapterDescriptor:
    """Prove exact reviewed class, constructed identity, and that status() is live."""

    try:
        descriptor = adapter_descriptor(adapter_id)
    except ValueError as exc:
        raise AdapterBindingError(str(exc)) from exc
    try:
        identity = _implementation_adapter_id(adapter)
        if identity != descriptor.adapter_id:
            raise AdapterBindingError(
                f"adapter identity {identity!r} does not match descriptor "
                f"{descriptor.adapter_id!r}"
            )
        if not callable(_require_status(adapter)):
            raise AdapterBindingError(
                f"worker adapter {descriptor.adapter_id!r} does not expose status"
            )
        implementation = adapter_implementation(descriptor.adapter_id)
        if type(adapter) is not implementation:
            raise AdapterBindingError(
                f"{type(adapter).__name__} is not the reviewed implementation "
                f"{implementation.__module__}.{implementation.__qualname__} "
                f"for {descriptor.adapter_id!r}"
            )
        constructed = (
            _codex_constructed_adapters()
            if descriptor.adapter_id == "codex-cli"
            else _CONSTRUCTED_REVIEWED_ADAPTERS
        )
        if adapter not in constructed:
            raise AdapterBindingError(
                f"{implementation.__qualname__} instance was not constructed "
                f"by the reviewed class for {descriptor.adapter_id!r}"
            )
        return descriptor
    except AdapterBindingError:
        raise
    except Exception as exc:
        raise AdapterBindingError(
            f"worker adapter {descriptor.adapter_id!r} failed to bind"
        ) from exc


@runtime_checkable
class WorkerExecutionAdapter(Protocol):
    """Minimum process adapter consumed by :class:`ExecutiveSupervisor`."""

    adapter_id: str
    inspector: ProcessInspector

    async def start(self, spec: WorkerLaunchSpec) -> WorkerProcessRef: ...

    async def status(self, ref: WorkerProcessRef) -> WorkerRunStatus: ...

    async def collect_result(self, ref: WorkerProcessRef) -> CollectionReceipt: ...

    async def cancel(self, ref: WorkerProcessRef, reason: str) -> CancelReceipt: ...

    async def run_validation_argv(
        self,
        spec: WorkerLaunchSpec,
        argv: Sequence[str],
        *,
        timeout_seconds: float = 300.0,
    ) -> ValidationReceipt: ...


@runtime_checkable
class RecoverableWorkerExecutionAdapter(WorkerExecutionAdapter, Protocol):
    """Optional same-execution recovery on top of the stable adapter/v1 floor."""

    def reattach(
        self, spec: WorkerLaunchSpec, binding: WorkerRecoveryBinding
    ) -> WorkerProcessRef: ...


__all__ = [
    "ADAPTER_DESCRIPTORS",
    "ADAPTER_INTERFACE_VERSION",
    "AdapterBindingError",
    "AdapterDescriptor",
    "WorkerExecutionAdapter",
    "RecoverableWorkerExecutionAdapter",
    "adapter_descriptor",
    "adapter_implementation",
    "bind_reviewed_adapter",
    "construct_reviewed_adapter",
]
