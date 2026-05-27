"""DTOs for the configurable intake form schema.

Used both for serving the rendered form to all users (`/api/meta/form-schema`)
and for admin reads/writes of the customization (`/api/admin/form-schema`).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FieldType = Literal["text", "textarea", "select", "boolean"]


class SelectOption(BaseModel):
    value: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=200)


class FormFieldIn(BaseModel):
    """A single form field as sent by admin.

    `source` is accepted for round-trip compatibility (GET responses include
    it as a UI hint) but the value is ignored — the server re-derives whether
    a field is core or custom from CORE_FIELD_NAMES.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=200)
    type: FieldType
    required: bool = False
    options: list[SelectOption] | None = None
    # Conditional visibility (preserved for core fields; not editable by admin).
    visible_if: dict[str, Any] | None = None
    source: Literal["core", "custom"] | None = None


class FormSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    fields: list[FormFieldIn]


class FormSchemaIn(BaseModel):
    """Incoming schema payload from the admin editor."""

    model_config = ConfigDict(extra="forbid")

    sections: list[FormSectionIn] = Field(min_length=1)


# --- Outgoing shapes -------------------------------------------------------


class FormFieldOut(BaseModel):
    name: str
    label: str
    type: FieldType
    required: bool = False
    options: list[SelectOption] | None = None
    visible_if: dict[str, Any] | None = None
    # Indicates whether this field is built-in ("core") or custom. Frontend
    # uses this to lock certain editor controls.
    source: Literal["core", "custom"] = "custom"


class FormSectionOut(BaseModel):
    id: str
    title: str
    fields: list[FormFieldOut]


class FormSchemaOut(BaseModel):
    """The merged schema served to every authenticated user."""

    sections: list[FormSectionOut]


class FormSchemaConfigOut(BaseModel):
    """Admin-facing view of the saved customization plus metadata."""

    sections: list[FormSectionOut]
    is_customized: bool
    updated_at: datetime | None = None
    updated_by_id: int | None = None
    updated_by_username: str | None = None


class FormSchemaAdminBundle(BaseModel):
    """Everything the admin editor needs in one round trip."""

    current: FormSchemaConfigOut
    default: FormSchemaOut
    core_field_names: list[str]
