"""Model-capability tags: what a model takes, makes and does, each with its evidence.

One :class:`ModelCapabilityTags` record describes one model on six axes
(input modalities, output modalities, capabilities, model type and role, task,
domain) plus two cost/routing flags (``free``, ``router``). Every tag carries
at least one :class:`TagEvidence` naming the source that stated it. A value no
source states is simply absent: a reader renders nothing for it and never
guesses.

Vocabularies (aligned with existing catalogs rather than invented):

* **Modalities** -- the models.dev ``Modality`` enum (``text``, ``image``,
  ``audio``, ``video``, ``pdf``) plus the output-side terms only specialist
  models produce: ``embeddings`` (OpenRouter's spelling), ``masks``
  (segmentation), ``scores`` (rerank and classification) and ``tensor``
  (gridded or time-series surrogate output).
* **Model type** -- LiteLLM ``mode`` spellings where one exists
  (``chat``, ``embedding``, ``rerank``, ``audio_transcription``,
  ``audio_speech``, ``image_generation``, ...), extended with the specialist
  types LiteLLM has no mode for (``segmentation``, ``classification``,
  ``forecasting``, ``scientific_surrogate``).
* **Role** -- ``general`` (a ``chat`` model: it can hold a conversation) or
  ``surrogate`` (every other model type: it does one task).
* **Task** -- Hugging Face Hub ``pipeline_tag`` ids verbatim
  (``huggingface.js`` ``PIPELINE_DATA``), or a ``clio:<id>`` for a task the
  Hub has no term for (e.g. ``clio:weather-emulation``).
* **Capability** -- a small closed set, each mapped from models.dev booleans,
  LiteLLM ``supports_*`` flags and OpenRouter ``supported_parameters``.
* **Domain** -- a small closed list; no maintained vocabulary exists.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Where a tag's evidence came from. Mirrors clio-agent's ``FactSource``
#: without its ``"unknown"`` member: a tag exists only because a source stated
#: it, so an unknown source can never carry one.
EvidenceSource = Literal[
    "user",
    "overlay",
    "server_report",
    "hf_repo",
    "models.dev",
    "litellm",
    "db",
    "openrouter",
    "dialect",
    "probe",
    "catalog",
]

#: What a model reads or produces.
Modality = Literal[
    "text",
    "image",
    "audio",
    "video",
    "pdf",
    "embeddings",
    "masks",
    "scores",
    "tensor",
]

#: What kind of model it is (LiteLLM ``mode`` spellings, extended).
ModelType = Literal[
    "chat",
    "embedding",
    "rerank",
    "audio_transcription",
    "audio_speech",
    "image_generation",
    "image_edit",
    "video_generation",
    "moderation",
    "ocr",
    "segmentation",
    "classification",
    "forecasting",
    "scientific_surrogate",
    "other",
]

#: ``general`` can hold a conversation; ``surrogate`` does one task.
Role = Literal["general", "surrogate"]

#: The model types whose role is ``general``. Every other type is a surrogate.
GENERAL_MODEL_TYPES: frozenset[str] = frozenset({"chat"})

#: What a model can do beyond reading and producing its modalities.
Capability = Literal[
    "tool_calling",
    "parallel_tool_calls",
    "reasoning",
    "structured_output",
    "web_search",
    "code_execution",
    "computer_use",
    "prompt_caching",
]

#: Subject domains a model is built for.
Domain = Literal[
    "language",
    "vision",
    "speech",
    "biology",
    "chemistry",
    "materials",
    "climate",
    "physics",
    "astronomy",
    "geoscience",
    "medical",
]

#: Hugging Face Hub ``pipeline_tag`` ids (``huggingface.js``
#: ``packages/tasks/src/pipelines.ts`` ``PIPELINE_DATA``, 57 keys).
HF_PIPELINE_TAGS: tuple[str, ...] = (
    # nlp
    "text-classification",
    "token-classification",
    "table-question-answering",
    "question-answering",
    "zero-shot-classification",
    "translation",
    "summarization",
    "feature-extraction",
    "text-generation",
    "fill-mask",
    "sentence-similarity",
    "table-to-text",
    "multiple-choice",
    "text-ranking",
    "text-retrieval",
    # audio
    "text-to-speech",
    "text-to-audio",
    "automatic-speech-recognition",
    "audio-to-audio",
    "audio-classification",
    "voice-activity-detection",
    # multimodal
    "audio-text-to-text",
    "image-text-to-text",
    "image-text-to-image",
    "image-text-to-video",
    "visual-question-answering",
    "document-question-answering",
    "video-text-to-text",
    "visual-document-retrieval",
    "any-to-any",
    # cv
    "depth-estimation",
    "image-classification",
    "object-detection",
    "image-segmentation",
    "text-to-image",
    "image-to-text",
    "image-to-image",
    "image-to-video",
    "unconditional-image-generation",
    "video-classification",
    "text-to-video",
    "zero-shot-image-classification",
    "mask-generation",
    "zero-shot-object-detection",
    "text-to-3d",
    "image-to-3d",
    "image-feature-extraction",
    "keypoint-detection",
    "video-to-video",
    # tabular
    "tabular-classification",
    "tabular-regression",
    "tabular-to-text",
    "time-series-forecasting",
    # rl
    "reinforcement-learning",
    "robotics",
    # other
    "graph-ml",
    "other",
)

#: A task id: a Hub ``pipeline_tag`` verbatim, or ``clio:<kebab-id>`` for a gap.
TASK_ID_PATTERN = "^(?:" + "|".join(HF_PIPELINE_TAGS) + r"|clio:[a-z0-9]+(?:-[a-z0-9]+)*)$"


class _ClosedRecord(BaseModel):
    """Strict wire semantics, identical to ``models.ClioSchemaBase``.

    Declared here (as :mod:`clio_schemas.gact_v3` does) because
    :mod:`clio_schemas.models` imports this module for ``EXPORTED_MODELS``.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def role_for_model_type(model_type: str) -> Role:
    """``general`` for a conversational model type, ``surrogate`` for any other."""

    return "general" if model_type in GENERAL_MODEL_TYPES else "surrogate"


class TagEvidence(_ClosedRecord):
    """One source's statement behind a tag."""

    source: EvidenceSource = Field(description="Who stated the value.")
    detail: str = Field(
        description=(
            "The upstream field and value as the source stated it, e.g. "
            "\"openrouter architecture.output_modalities=['decisions']\" or "
            "\"ALCF gateway /models framework='sam3service'\"."
        )
    )
    observed_at: str = Field(
        description="ISO-8601 time the evidence was produced (empty when the source gives none)."
    )


def _evidence() -> Any:
    """The ``evidence`` field every tag declares: one or more statements."""

    return Field(
        min_length=1,
        description="Every source that states this value; the first is the winning one.",
    )


class ModalityTag(_ClosedRecord):
    """A modality the model reads or produces."""

    value: Modality
    evidence: list[TagEvidence] = _evidence()


class CapabilityTag(_ClosedRecord):
    """A capability the model has."""

    value: Capability
    evidence: list[TagEvidence] = _evidence()


class ModelTypeTag(_ClosedRecord):
    """What kind of model it is."""

    value: ModelType
    evidence: list[TagEvidence] = _evidence()


class RoleTag(_ClosedRecord):
    """Whether the model holds a conversation (general) or does one task (surrogate)."""

    value: Role
    evidence: list[TagEvidence] = _evidence()


class TaskTag(_ClosedRecord):
    """A task the model performs, as a Hugging Face ``pipeline_tag`` id (or ``clio:<id>``)."""

    value: str = Field(pattern=TASK_ID_PATTERN)
    evidence: list[TagEvidence] = _evidence()


class DomainTag(_ClosedRecord):
    """A subject domain the model is built for."""

    value: Domain
    evidence: list[TagEvidence] = _evidence()


class FlagTag(_ClosedRecord):
    """A yes/no fact about how the model is offered (free of charge, a router)."""

    value: bool
    evidence: list[TagEvidence] = _evidence()


def _unique(
    name: str, tags: list[ModalityTag] | list[CapabilityTag] | list[TaskTag] | list[DomainTag]
) -> None:
    values = [tag.value for tag in tags]
    if len(values) != len(set(values)):
        raise ValueError(f"{name} repeats a value: {values}")


class ModelCapabilityTags(_ClosedRecord):
    """Everything a model picker may tag one model with, each tag with its evidence.

    An absent tag means no source stated it -- never "no". ``role`` always
    agrees with ``model_type`` when both are present (``chat`` is general,
    every other type a surrogate).
    """

    model_key: str = Field(
        min_length=1,
        description=(
            "The canonical model identity the tags describe (a Hub repo id, a cloud model id, ...)."
        ),
    )
    model_type: ModelTypeTag | None = Field(default=None, description="What kind of model it is.")
    role: RoleTag | None = Field(default=None, description="general or surrogate.")
    tasks: list[TaskTag] = Field(default_factory=list, description="Tasks it performs.")
    input_modalities: list[ModalityTag] = Field(default_factory=list, description="What it reads.")
    output_modalities: list[ModalityTag] = Field(
        default_factory=list, description="What it produces."
    )
    capabilities: list[CapabilityTag] = Field(default_factory=list, description="What it can do.")
    domains: list[DomainTag] = Field(default_factory=list, description="Subject domains.")
    free: FlagTag | None = Field(
        default=None, description="Whether this endpoint serves the model at no cost."
    )
    router: FlagTag | None = Field(
        default=None,
        description="Whether the model id is a router that picks another model per request.",
    )

    @model_validator(mode="after")
    def _consistent(self) -> ModelCapabilityTags:
        _unique("tasks", self.tasks)
        _unique("input_modalities", self.input_modalities)
        _unique("output_modalities", self.output_modalities)
        _unique("capabilities", self.capabilities)
        _unique("domains", self.domains)
        if self.model_type is not None and self.role is not None:
            expected = role_for_model_type(self.model_type.value)
            if self.role.value != expected:
                raise ValueError(
                    f"role {self.role.value!r} contradicts model_type "
                    f"{self.model_type.value!r} (expected {expected!r})"
                )
        return self


__all__ = [
    "GENERAL_MODEL_TYPES",
    "HF_PIPELINE_TAGS",
    "TASK_ID_PATTERN",
    "Capability",
    "CapabilityTag",
    "Domain",
    "DomainTag",
    "EvidenceSource",
    "FlagTag",
    "Modality",
    "ModalityTag",
    "ModelCapabilityTags",
    "ModelType",
    "ModelTypeTag",
    "Role",
    "RoleTag",
    "TagEvidence",
    "TaskTag",
    "role_for_model_type",
]
