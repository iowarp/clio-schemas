"""Canonical GACT 0.3 message-block vocabulary."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class _ClosedBlock(BaseModel):
    """Shared strict fields carried by every GACT 0.3 message block."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    id: str
    agent_id: str | None = None
    sequence: int | None = Field(default=None, gt=0)
    stream_source: str | None = None
    channel: str | None = None


class TextMessageBlock(_ClosedBlock):
    """Assistant or user prose."""

    type: Literal["text"]
    text: str
    streaming: bool | None = None


class ReasoningMessageBlock(_ClosedBlock):
    """Provider reasoning or semantic next-thought narration."""

    type: Literal["reasoning"]
    text: str
    streaming: bool | None = None
    source: str | None = None
    provider_source: str | None = None
    default_collapsed: bool | None = None


class ToolMessageBlock(_ClosedBlock):
    """Reference to one tool invocation."""

    type: Literal["tool"]
    tool_id: str
    thought: str | None = None


class PlanMessageBlock(_ClosedBlock):
    """Plan content emitted in causal order."""

    type: Literal["plan"]
    title: str
    detail: str | None = None


class TaskMessageBlock(_ClosedBlock):
    """Reference to one task."""

    type: Literal["task"]
    task_id: str


class SubagentMessageBlock(_ClosedBlock):
    """Reference to one child-agent run."""

    type: Literal["subagent"]
    subagent_id: str


class ArtifactMessageBlock(_ClosedBlock):
    """Reference to one artifact."""

    type: Literal["artifact"]
    artifact_id: str


class ActionCardBehavior(BaseModel):
    """Registered action-card behavior with forward-compatible parameters."""

    model_config = ConfigDict(extra="allow", strict=True, frozen=True)

    kind: str
    handle_id: str | None = None
    reason: str | None = None


class ActionCardAction(BaseModel):
    """One action exposed by an action card."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    id: str
    label: str
    enabled: bool = True
    behavior: ActionCardBehavior


class ActionCardMessageBlock(_ClosedBlock):
    """Interactive action-card block."""

    type: Literal["action_card"]
    title: str
    detail: str | None = None
    source: str | None = None
    severity: str | None = None
    status: str | None = None
    actions: list[ActionCardAction]


class A2UIMessageBlock(_ClosedBlock):
    """Reference to one durable A2UI surface."""

    type: Literal["a2ui"]
    surface_id: str


class CitationMessageBlock(_ClosedBlock):
    """Citation label and target URI."""

    type: Literal["citation"]
    label: str
    uri: str


class DiffMessageBlock(_ClosedBlock):
    """Unified file diff."""

    type: Literal["diff"]
    path: str
    unified_diff: str


class ErrorMessageBlock(_ClosedBlock):
    """Typed, recoverable or terminal error."""

    type: Literal["error"]
    code: str
    message: str
    recoverable: bool


class RoutingMessageBlock(_ClosedBlock):
    """Routing or compaction metadata visible to the user."""

    type: Literal["routing"]
    label: str
    detail: str | None = None


MessageBlockValue = Annotated[
    TextMessageBlock
    | ReasoningMessageBlock
    | ToolMessageBlock
    | PlanMessageBlock
    | TaskMessageBlock
    | SubagentMessageBlock
    | ArtifactMessageBlock
    | ActionCardMessageBlock
    | A2UIMessageBlock
    | CitationMessageBlock
    | DiffMessageBlock
    | ErrorMessageBlock
    | RoutingMessageBlock,
    Field(discriminator="type"),
]


class MessageBlock(RootModel[MessageBlockValue]):
    """Closed discriminated union of the 13 GACT 0.3 message-block types."""
