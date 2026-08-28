from __future__ import annotations

import copy
from typing import Any


def to_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Harden a Pydantic-generated JSON Schema into an Anthropic strict tool
    `input_schema`.

    Strict tool use (Anthropic) guarantees the returned `tool_use.input` validates
    against the schema exactly, which is only true if every object node forbids
    extra properties and requires all of its declared properties. Pydantic's
    `model_json_schema()` doesn't set either by default (fields with defaults are
    left optional, and `additionalProperties` is only emitted for models with
    `extra="forbid"`), so this walks the schema - including `$defs` - and forces
    both, recursively.

    Anthropic's strict-schema validator also rejects numeric range keywords
    (`minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum`) - "For 'integer'
    type, properties maximum, minimum are not supported" - so those are stripped
    and folded into `description` instead, to keep the constraint visible to the
    model even though it's no longer mechanically enforced.
    """
    hardened = copy.deepcopy(schema)
    RANGE_KEYS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")

    def harden(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"].keys())
            for prop_schema in node["properties"].values():
                harden(prop_schema)
        if "items" in node:
            harden(node["items"])
        for key in ("anyOf", "oneOf", "allOf"):
            for sub in node.get(key, []):
                harden(sub)
        if node.get("type") in ("integer", "number"):
            present = {key: node.pop(key) for key in RANGE_KEYS if key in node}
            if present:
                range_note = ", ".join(f"{key}={value}" for key, value in present.items())
                node["description"] = f"{node.get('description', '')} ({range_note})".strip()

    for def_schema in hardened.get("$defs", {}).values():
        harden(def_schema)
    harden(hardened)
    return hardened


def constrain_id_field(schema: dict[str, Any], def_name: str, prop_name: str, valid_values: list[str]) -> None:
    """Restrict a string (or nullable-string) property to a fixed set of values.

    Use this to bind an ID field - e.g. `bullet_id` - to the exact IDs that exist
    in the current request (master resume bullet IDs, selected bullet IDs, ...).
    An `enum` is a real JSON Schema constraint the model is validated against
    server-side, not a prompt instruction it can ignore - so a request-scoped ID
    fabricated outside that set is rejected before it ever reaches application
    code, instead of surfacing later as a `validate_against_*` ValueError.

    Mutates `schema` in place. Handles both a plain `{"type": "string"}` node and
    a nullable `anyOf: [{"type": "string"}, {"type": "null"}]` node (the shape
    Pydantic emits for `str | None` fields).
    """
    node = schema["$defs"][def_name]["properties"][prop_name]
    targets = node.get("anyOf", [node])
    for target in targets:
        if target.get("type") == "string":
            target["enum"] = list(valid_values)


def constrain_id_array_items(schema: dict[str, Any], def_name: str, prop_name: str, valid_values: list[str]) -> None:
    """Same as `constrain_id_field`, but for a `list[str]` property's items."""
    schema["$defs"][def_name]["properties"][prop_name]["items"]["enum"] = list(valid_values)
