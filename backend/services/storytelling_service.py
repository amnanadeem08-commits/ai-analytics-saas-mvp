from __future__ import annotations

from typing import Any


def build_business_story(executive_summary: dict[str, Any]) -> dict[str, Any]:
    decision_blocks = executive_summary.get("decision_framework", [])
    findings = executive_summary.get("key_findings", [])
    risks = executive_summary.get("risks", [])
    opportunities = executive_summary.get("opportunities", [])
    recommendations = executive_summary.get("recommendations", [])

    lead_block = decision_blocks[0] if decision_blocks else {}
    story_points = []
    for block in decision_blocks[:4]:
        story_points.append(
            {
                "title": block.get("metric", "Business signal"),
                "narrative": (
                    f"{block.get('what_happened', '')} "
                    f"{block.get('why_it_happened', '')} "
                    f"Recommended next step: {block.get('what_to_do', '')}"
                ).strip(),
                "evidence": block.get("evidence", {}),
                "confidence": block.get("confidence", executive_summary.get("confidence", "low")),
            }
        )

    return {
        "data_story": lead_block.get("what_happened", executive_summary.get("insight", "")),
        "trend_story": lead_block.get("expected_impact", ""),
        "business_story": (
            f"{executive_summary.get('insight', '')} {executive_summary.get('reason', '')} "
            f"{executive_summary.get('action', '')}"
        ).strip(),
        "executive_narrative": {
            "opening": executive_summary.get("insight", ""),
            "evidence": [item.get("finding") for item in findings[:3] if item.get("finding")],
            "risks": [item.get("risk") for item in risks[:3] if item.get("risk")],
            "opportunities": [item.get("opportunity") for item in opportunities[:3] if item.get("opportunity")],
            "recommendations": [
                item.get("recommendation") for item in recommendations[:3] if item.get("recommendation")
            ],
        },
        "story_points": story_points,
    }
