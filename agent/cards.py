"""Card builders for ASI:One Dynamic UI using Element-Tree primitives."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import uuid4

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    MetadataContent,
    TextContent,
)

from schemas.results import SchemeEvaluation

CARD_PROTOCOL_VERSION = "1"
CIVICBRIDGE_SOURCE = "civicbridge_ui"


def _variant_for_status(status: str) -> str:
    if status == "ELIGIBLE":
        return "success"
    if status == "LIKELY_ELIGIBLE":
        return "info"
    if status == "POTENTIALLY_ELIGIBLE":
        return "warning"
    return "danger"


def build_scheme_list_payload(
    evaluations: List[SchemeEvaluation],
    title: str = "Government Schemes & Benefits",
    subtitle: Optional[str] = "Select a scheme below to view customized documents and application steps.",
) -> dict[str, Any]:
    """Build the card_payload dictionary for an interactive scheme list in ASI:One."""
    items: List[dict[str, Any]] = []

    for item in evaluations:
        status_variant = _variant_for_status(item.overall_status)
        badge_label = f"{item.overall_status.replace('_', ' ')}"
        if item.benefit_amount:
            badge_label += f" • {item.benefit_amount}"

        items.append(
            {
                "children": [
                    {
                        "type": "group",
                        "direction": "column",
                        "gap": 8,
                        "children": [
                            {
                                "type": "heading",
                                "value": f"{item.short_name}: {item.scheme_name}",
                                "level": 3,
                            },
                            {
                                "type": "badge",
                                "label": badge_label,
                                "variant": status_variant,
                            },
                            {
                                "type": "text",
                                "value": item.benefit_summary,
                                "style": "body",
                            },
                            {
                                "type": "text",
                                "value": f"Coverage: {item.geographic_coverage} | Official Portal: {item.official_portal_url}",
                                "style": "muted",
                            },
                        ],
                    },
                    {
                        "type": "button",
                        "label": f"View Checklist ({item.short_name})",
                        "primary": item.overall_status in ("ELIGIBLE", "LIKELY_ELIGIBLE"),
                        "action": {
                            "selection": {
                                "action": "view_checklist",
                                "scheme_id": item.scheme_id,
                                "source": CIVICBRIDGE_SOURCE,
                            }
                        },
                    },
                ]
            }
        )

    section: dict[str, Any] = {
        "type": "section",
        "title": title,
        "children": [
            {
                "type": "list",
                "items": items,
            }
        ],
    }
    if subtitle:
        section["subtitle"] = subtitle

    return {"root": section}


def build_scheme_detail_payload(plan: dict[str, Any]) -> dict[str, Any]:
    """Build the card_payload for a detailed application checklist card."""
    docs_formatted = "\n".join(f"• {doc}" for doc in plan.get("documents_checklist", []))
    steps_formatted = "\n".join(
        f"{idx + 1}. {step}" for idx, step in enumerate(plan.get("application_steps", []))
    )

    section: dict[str, Any] = {
        "type": "section",
        "title": f"Application Plan: {plan.get('short_name')}",
        "subtitle": plan.get("scheme_name"),
        "children": [
            {
                "type": "group",
                "direction": "column",
                "gap": 12,
                "children": [
                    {
                        "type": "badge",
                        "label": f"Status: {plan.get('eligibility_status', '').replace('_', ' ')}",
                        "variant": _variant_for_status(plan.get("eligibility_status", "")),
                    },
                    {
                        "type": "heading",
                        "value": "Benefit Overview",
                        "level": 3,
                    },
                    {
                        "type": "text",
                        "value": plan.get("benefit_summary", ""),
                        "style": "body",
                    },
                    {"type": "divider"},
                    {
                        "type": "heading",
                        "value": "Required Documents Checklist",
                        "level": 3,
                    },
                    {
                        "type": "text",
                        "value": docs_formatted or "Standard government ID and bank passbook required.",
                        "style": "body",
                    },
                    {"type": "divider"},
                    {
                        "type": "heading",
                        "value": "Application Instructions",
                        "level": 3,
                    },
                    {
                        "type": "text",
                        "value": steps_formatted or "Apply through the official portal.",
                        "style": "body",
                    },
                    {"type": "divider"},
                    {
                        "type": "text",
                        "value": f"Official Portal: {plan.get('official_portal_url')}\nTimeline: {plan.get('application_dates')}\nLast Verified: {plan.get('last_verified')}",
                        "style": "muted",
                    },
                ],
            },
            {
                "type": "group",
                "direction": "row",
                "gap": 8,
                "children": [
                    {
                        "type": "button",
                        "label": "Back to Schemes List",
                        "primary": False,
                        "action": {
                            "selection": {
                                "action": "back_to_schemes",
                                "source": CIVICBRIDGE_SOURCE,
                            }
                        },
                    }
                ],
            },
        ],
    }
    return {"root": section}


def build_card_metadata(payload: dict[str, Any]) -> MetadataContent:
    """Format dictionary payload into MetadataContent compliant with Agentverse."""
    return MetadataContent(
        type="metadata",
        metadata={
            "card_protocol_version": CARD_PROTOCOL_VERSION,
            "requires_card_interaction": "true",
            "card_kind": "custom",
            "card_payload": json.dumps(payload),
        },
    )


def create_schemes_list_chat_message(
    markdown_text: str, evaluations: List[SchemeEvaluation]
) -> ChatMessage:
    """Create ChatMessage containing both markdown text and interactive list card."""
    payload = build_scheme_list_payload(evaluations)
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=markdown_text),
            build_card_metadata(payload),
        ],
    )


def create_scheme_detail_chat_message(
    markdown_text: str, plan: dict[str, Any]
) -> ChatMessage:
    """Create ChatMessage containing both detailed markdown and interactive detail card."""
    payload = build_scheme_detail_payload(plan)
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=markdown_text),
            build_card_metadata(payload),
        ],
    )
