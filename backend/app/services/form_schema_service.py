"""Configurable form schema: read, validate, persist.

This service is the single source of truth for "what does the intake form
actually look like right now?" It merges admin customizations on top of the
shipped default schema, and enforces the core-field invariants so the form
stays compatible with `IntakePayload` and the risk rules.

Invariants enforced on every save:
  - Every core field (those required by `IntakePayload`) is present exactly
    once, somewhere in the schema. Admins may relabel a core field and move
    it into a different section, but they cannot remove it.
  - A core field's `type`, `required`, `options`, and `visible_if` are
    re-derived from the default schema on save — this means admins can't
    accidentally (or maliciously) change the semantics of a field the
    backend already depends on.
  - Custom field names are unique across the whole schema, match
    `^[a-z][a-z0-9_]{0,49}$`, and don't collide with core field names.
  - Custom select fields have at least one option.
  - Section IDs are unique.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.form_schema import CORE_FIELD_NAMES, CORE_FIELDS, default_schema
from app.models.form_schema_config import FormSchemaConfig
from app.models.user import User
from app.repositories import form_schema_configs as repo

_CUSTOM_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
# Reserved names that, while not part of the current core schema, must never
# be used as custom field names to avoid future collisions.
_RESERVED_NAMES: frozenset[str] = frozenset(
    {
        "id",
        "created_by_id",
        "created_at",
        "updated_at",
        "status",
        "payload",
        "risk_level",
        "risk_reasons",
    }
)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def _annotate_source(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tag each field with source=core|custom for the frontend."""
    out: list[dict[str, Any]] = []
    for s in sections:
        out_fields = []
        for f in s["fields"]:
            f2 = dict(f)
            f2["source"] = "core" if f["name"] in CORE_FIELD_NAMES else "custom"
            out_fields.append(f2)
        out.append({"id": s["id"], "title": s["title"], "fields": out_fields})
    return out


def get_active_sections(db: Session) -> list[dict[str, Any]]:
    """Return the schema currently served to all users (annotated)."""
    row = repo.get(db)
    sections = row.sections if row else default_schema()
    return _annotate_source(sections)


def get_admin_view(db: Session) -> dict[str, Any]:
    """Bundle saved schema + default + core-field list for the admin editor."""
    row = repo.get(db)
    current_sections = _annotate_source(row.sections if row else default_schema())
    default_sections = _annotate_source(default_schema())

    updated_by_username: str | None = None
    if row and row.updated_by is not None:
        updated_by_username = row.updated_by.username

    return {
        "current": {
            "sections": current_sections,
            "is_customized": row is not None,
            "updated_at": row.updated_at if row else None,
            "updated_by_id": row.updated_by_id if row else None,
            "updated_by_username": updated_by_username,
        },
        "default": {"sections": _annotate_source(default_schema())},
        "core_field_names": sorted(CORE_FIELD_NAMES),
    }


# ---------------------------------------------------------------------------
# Validate + write
# ---------------------------------------------------------------------------


def _validation_error(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def _canonicalize_core_field(name: str, label: str) -> dict[str, Any]:
    """Take admin's label, but force all other properties to the defaults."""
    default = CORE_FIELDS[name]
    out: dict[str, Any] = {
        "name": name,
        "label": label,
        "type": default["type"],
    }
    if default.get("required"):
        out["required"] = True
    if "options" in default:
        out["options"] = [dict(o) for o in default["options"]]
    if "visible_if" in default:
        out["visible_if"] = dict(default["visible_if"])
    return out


def _validate_custom_field(field: dict[str, Any]) -> dict[str, Any]:
    name = field["name"]
    if not _CUSTOM_NAME_RE.match(name):
        raise _validation_error(
            f"Custom field name '{name}' is invalid. Use lowercase letters, "
            "digits, and underscores; start with a letter; max 50 chars."
        )
    if name in CORE_FIELD_NAMES:
        raise _validation_error(
            f"'{name}' is a built-in field and can't be used as a custom name."
        )
    if name in _RESERVED_NAMES:
        raise _validation_error(f"'{name}' is a reserved name.")

    f_type = field["type"]
    out: dict[str, Any] = {
        "name": name,
        "label": field["label"],
        "type": f_type,
        "required": bool(field.get("required", False)),
    }
    if f_type == "select":
        options = field.get("options") or []
        if not options:
            raise _validation_error(
                f"Custom select field '{name}' must have at least one option."
            )
        seen_values: set[str] = set()
        cleaned: list[dict[str, str]] = []
        for o in options:
            v, label = o["value"], o["label"]
            if v in seen_values:
                raise _validation_error(
                    f"Field '{name}' has duplicate option value '{v}'."
                )
            seen_values.add(v)
            cleaned.append({"value": v, "label": label})
        out["options"] = cleaned
    return out


def validate_and_canonicalize(incoming: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the admin payload and return the canonicalized sections list.

    The returned shape is what's persisted to `form_schema_configs.sections`.
    """
    sections_in: list[dict[str, Any]] = incoming.get("sections") or []
    if not sections_in:
        raise _validation_error("Schema must have at least one section.")

    seen_section_ids: set[str] = set()
    seen_field_names: set[str] = set()
    core_seen: set[str] = set()
    out_sections: list[dict[str, Any]] = []

    for s in sections_in:
        sid = s["id"]
        if sid in seen_section_ids:
            raise _validation_error(f"Duplicate section id '{sid}'.")
        seen_section_ids.add(sid)
        if not s.get("title", "").strip():
            raise _validation_error(f"Section '{sid}' must have a title.")

        out_fields: list[dict[str, Any]] = []
        for f in s["fields"]:
            name = f["name"]
            if name in seen_field_names:
                raise _validation_error(
                    f"Field name '{name}' is used more than once."
                )
            seen_field_names.add(name)
            if not f.get("label", "").strip():
                raise _validation_error(f"Field '{name}' must have a label.")
            if name in CORE_FIELD_NAMES:
                out_fields.append(_canonicalize_core_field(name, f["label"]))
                core_seen.add(name)
            else:
                out_fields.append(_validate_custom_field(f))
        out_sections.append({"id": sid, "title": s["title"], "fields": out_fields})

    missing_core = CORE_FIELD_NAMES - core_seen
    if missing_core:
        raise _validation_error(
            "These required built-in fields are missing from the schema: "
            + ", ".join(sorted(missing_core))
        )

    return out_sections


def save(db: Session, user: User, incoming: dict[str, Any]) -> dict[str, Any]:
    canonical_sections = validate_and_canonicalize(incoming)
    row = repo.get(db)
    if row is None:
        row = FormSchemaConfig(sections=canonical_sections, updated_by_id=user.id)
    else:
        row.sections = canonical_sections
        row.updated_by_id = user.id
    repo.save(db, row)
    return get_admin_view(db)


def reset(db: Session) -> dict[str, Any]:
    row = repo.get(db)
    if row is not None:
        repo.delete(db, row)
    return get_admin_view(db)


# ---------------------------------------------------------------------------
# Submit-time validation for custom fields
# ---------------------------------------------------------------------------


def validate_custom_payload(
    db: Session, payload: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Return Pydantic-style errors for custom fields in `payload`.

    The core fields are already validated by `IntakePayload`. This adds:
      - Required-ness for custom fields.
      - Type coercion sanity checks (string/bool/select option value).

    Errors mimic Pydantic's `loc/msg/type` shape so they can be merged into
    a single 422 response on the API.
    """
    sections = get_active_sections(db)
    errors: list[dict[str, Any]] = []
    for s in sections:
        for f in s["fields"]:
            if f["source"] == "core":
                continue
            name = f["name"]
            value = payload.get(name)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                if f.get("required"):
                    errors.append(
                        {
                            "loc": [name],
                            "msg": "Required",
                            "type": "missing",
                        }
                    )
                continue
            # Type sanity checks.
            t = f["type"]
            if t in ("text", "textarea") and not isinstance(value, str):
                errors.append({"loc": [name], "msg": "Must be a string", "type": "type_error"})
            elif t == "boolean" and not isinstance(value, bool):
                errors.append({"loc": [name], "msg": "Must be true or false", "type": "type_error"})
            elif t == "select":
                allowed = {o["value"] for o in (f.get("options") or [])}
                if not isinstance(value, str) or value not in allowed:
                    errors.append(
                        {
                            "loc": [name],
                            "msg": f"Must be one of: {sorted(allowed)}",
                            "type": "value_error.enum",
                        }
                    )
    return {"errors": errors}
