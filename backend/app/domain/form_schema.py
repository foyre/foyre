"""Canonical intake form schema.

The shape here is deliberately boring: a list of sections, each with a list of
fields. The frontend renders from this via `/api/meta/form-schema` so enums +
help text live in one place. This is *not* a dynamic form builder; adding a
field still means a code change in a Pydantic schema and (often) in risk rules.
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


FORM_SCHEMA: list[dict[str, Any]] = [
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
