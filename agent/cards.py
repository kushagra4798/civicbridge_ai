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

from schemas.results import SchemeEvaluation, EligibilityGrowthPlan

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
    title: str = "Government Opportunities & Benefits",
    subtitle: Optional[str] = "Select an opportunity below for customized documents, steps, or growth pathways.",
    growth_plan: Optional[EligibilityGrowthPlan] = None,
) -> dict[str, Any]:
    """Build the card_payload dictionary for an interactive scheme and internship list in ASI:One."""
    items: List[dict[str, Any]] = []

    # 1. High-leverage pathway banner if available
    if growth_plan and growth_plan.high_leverage_actions:
        hl_names = ", ".join(f"[{g.requirement_name}]" for g in growth_plan.high_leverage_actions[:2])
        items.append(
            {
                "children": [
                    {
                        "type": "group",
                        "direction": "column",
                        "gap": 6,
                        "children": [
                            {
                                "type": "badge",
                                "label": f"🚀 {len(growth_plan.high_leverage_actions)} High-Leverage Growth Action(s)",
                                "variant": "info",
                            },
                            {
                                "type": "text",
                                "value": f"Key pathways to unlock multiple opportunities: {hl_names}.",
                                "style": "body",
                            },
                        ],
                    }
                ]
            }
        )

    for item in evaluations:
        status_variant = _variant_for_status(item.overall_status)
        type_prefix = "💼 Internship" if item.opportunity_type == "internship" else "📜 Scheme"
        badge_label = f"{type_prefix} • {item.overall_status.replace('_', ' ')}"
        if item.stipend:
            badge_label += f" • {item.stipend}"
        elif item.benefit_amount:
            badge_label += f" • {item.benefit_amount}"

        desc_text = item.benefit_summary
        if item.host_type:
            host_str = "Government Department" if item.host_type == "government" else "Public/Private Sector via Official Portal"
            desc_text = f"Host: {host_str} | " + desc_text

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
                                "value": desc_text,
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

    type_tag = "Internship" if plan.get("opportunity_type") == "internship" else "Scheme"
    badge_label = f"{type_tag} • Status: {plan.get('eligibility_status', '').replace('_', ' ')}"
    if plan.get("stipend"):
        badge_label += f" • Stipend: {plan.get('stipend')}"

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
                        "label": badge_label,
                        "variant": _variant_for_status(plan.get("eligibility_status", "")),
                    },
                    {
                        "type": "heading",
                        "value": "Opportunity Overview",
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
                        "value": docs_formatted or "Standard identification and institutional bonafide required.",
                        "style": "body",
                    },
                    {"type": "divider"},
                    {
                        "type": "heading",
                        "value": "Official Application Procedure",
                        "level": 3,
                    },
                    {
                        "type": "text",
                        "value": steps_formatted or "Apply via official government portal.",
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
                        "label": "Back to Opportunities List",
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
    markdown_text: str,
    evaluations: List[SchemeEvaluation],
    growth_plan: Optional[EligibilityGrowthPlan] = None,
) -> ChatMessage:
    """Create ChatMessage containing both markdown text and interactive list card."""
    payload = build_scheme_list_payload(evaluations, growth_plan=growth_plan)
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
