"""Canonical default intake form schema.

This is the schema Foyre ships with out of the box. Admins can customize the
form via the admin UI; their customizations are stored in the
`form_schema_configs` table and merged with these defaults on read.

Core fields (those backing `IntakePayload` + risk evaluation) are LOCKED:
admins may relabel them and put them in any section, but cannot remove,
re-type, or change their `required`/`options`/`visible_if`. Custom fields
admins add live alongside in the same payload JSON.

Adding a new core field here is still a code change — both `IntakePayload`
and (often) the risk rules need to know about it.
"""
from __future__ import annotations

from typing import Any

from app.domain.enums import (
    DataClassification,
    Environment,
    WorkloadType,
    YesNoUnknown,
)


def _enum_options(enum_cls: type) -> list[dict[str, str]]:
    return [{"value": m.value, "label": m.value.replace("_", " ").title()} for m in enum_cls]


DEFAULT_FORM_SCHEMA: list[dict[str, Any]] = [
    {
        "id": "basics",
        "title": "Basics",
        "fields": [
            {"name": "application_name", "label": "Application name", "type": "text", "required": True},
            {"name": "business_owner", "label": "Business owner", "type": "text", "required": True},
            {"name": "technical_owner", "label": "Technical owner", "type": "text", "required": True},
            {"name": "team", "label": "Team / department", "type": "text", "required": True},
            {"name": "description", "label": "Short description", "type": "textarea", "required": True},
            {
                "name": "environment",
                "label": "Intended environment",
                "type": "select",
                "options": _enum_options(Environment),
                "required": True,
            },
        ],
    },
    {
        "id": "workload",
        "title": "AI workload",
        "fields": [
            {
                "name": "workload_type",
                "label": "Workload type",
                "type": "select",
                "options": _enum_options(WorkloadType),
                "required": True,
            },
        ],
    },
    {
        "id": "data_and_risk",
        "title": "Data & risk",
        "fields": [
            {
                "name": "handles_sensitive_data",
                "label": "Will the application handle sensitive data?",
                "type": "select",
                "options": _enum_options(YesNoUnknown),
                "required": True,
            },
            {
                "name": "data_classification",
                "label": "Data classification",
                "type": "select",
                "options": _enum_options(DataClassification),
                "required": True,
            },
            {"name": "uses_enterprise_documents", "label": "Uses enterprise documents?", "type": "boolean"},
            {"name": "uses_vector_db", "label": "Uses a vector database?", "type": "boolean"},
            {
                "name": "vector_db_name",
                "label": "Vector DB name / type",
                "type": "text",
                "visible_if": {"uses_vector_db": True},
            },
            {"name": "calls_external_model_api", "label": "Calls external AI/model APIs?", "type": "boolean"},
            {"name": "uses_internal_models", "label": "Uses internally hosted models?", "type": "boolean"},
            {"name": "takes_actions", "label": "Takes actions on behalf of a user/system?", "type": "boolean"},
            {"name": "internet_egress", "label": "Internet egress required?", "type": "boolean"},
            {"name": "gpu_required", "label": "GPU required?", "type": "boolean"},
        ],
    },
    {
        "id": "notes",
        "title": "Additional",
        "fields": [
            {"name": "justification", "label": "Notes / justification", "type": "textarea"},
            {"name": "timeline", "label": "Requested go-live timeline", "type": "text"},
            {"name": "architecture_notes", "label": "Architecture notes", "type": "textarea"},
        ],
    },
]


def _flatten_core_fields() -> dict[str, dict[str, Any]]:
    """Map of core field name -> field def, taken from DEFAULT_FORM_SCHEMA."""
    out: dict[str, dict[str, Any]] = {}
    for section in DEFAULT_FORM_SCHEMA:
        for field in section["fields"]:
            out[field["name"]] = dict(field)
    return out


# Public, frozen metadata: which field names ship with Foyre, and what their
# canonical (non-overridable) properties look like. Anything in this map is
# considered "core" and is protected from admin edits beyond relabeling /
# resectioning.
CORE_FIELDS: dict[str, dict[str, Any]] = _flatten_core_fields()
CORE_FIELD_NAMES: frozenset[str] = frozenset(CORE_FIELDS.keys())


def default_schema() -> list[dict[str, Any]]:
    """Return a deep-ish copy of the default schema (safe to mutate)."""
    return [
        {
            "id": section["id"],
            "title": section["title"],
            "fields": [dict(f) for f in section["fields"]],
        }
        for section in DEFAULT_FORM_SCHEMA
    ]


# Backwards-compatible alias. New code should use DEFAULT_FORM_SCHEMA.
FORM_SCHEMA = DEFAULT_FORM_SCHEMA
