from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DomainContext:
    detected_domain: str
    confidence: str
    confidence_score: float
    business_context: str
    industry: str
    domain_specific_kpis: list[dict[str, Any]] = field(default_factory=list)
    storyboard_template: dict[str, Any] = field(default_factory=dict)
    dashboard_template: dict[str, Any] = field(default_factory=dict)
    visualization_rules: dict[str, Any] = field(default_factory=dict)
    language_policy: dict[str, Any] = field(default_factory=dict)
    executive_summary_style: dict[str, Any] = field(default_factory=dict)
    recommended_questions: list[str] = field(default_factory=list)
    rag_context: dict[str, Any] = field(default_factory=dict)
    knowledge_pack_id: str | None = None
    benchmark_provider: str | None = None
    glossary_provider: str | None = None
    executive_guidance_provider: str | None = None
    detection_signals: list[str] = field(default_factory=list)
    dataset_classifier: dict[str, Any] = field(default_factory=dict)
    business_context_engine: dict[str, Any] = field(default_factory=dict)
    root_causes: list[dict[str, Any]] = field(default_factory=list)
    domain_mode: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        detection = {
            "domain": self.detected_domain,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "signals": list(self.detection_signals),
            "business_context": self.business_context,
            "industry": self.industry,
        }
        return {
            "domain_context": {
                "detected_domain": self.detected_domain,
                "confidence": self.confidence,
                "confidence_score": self.confidence_score,
                "business_context": self.business_context,
                "industry": self.industry,
                "domain_specific_kpis": self.domain_specific_kpis,
                "storyboard_template": self.storyboard_template,
                "dashboard_template": self.dashboard_template,
                "visualization_rules": self.visualization_rules,
                "language_policy": self.language_policy,
                "executive_summary_style": self.executive_summary_style,
                "recommended_questions": self.recommended_questions,
                "rag_context": self.rag_context,
                "knowledge_pack_id": self.knowledge_pack_id,
                "benchmark_provider": self.benchmark_provider,
                "glossary_provider": self.glossary_provider,
                "executive_guidance_provider": self.executive_guidance_provider,
            },
            "domain_detector": {
                "detected_domain": self.detected_domain,
                "confidence": self.confidence,
                "confidence_score": self.confidence_score,
                "signals": list(self.detection_signals),
            },
            "detection": detection,
            "business_context_engine": self.business_context_engine,
            "dataset_classifier": self.dataset_classifier,
            "dynamic_storyboard_template": self.storyboard_template,
            "dynamic_dashboard_template": self.dashboard_template,
            "domain_kpis": self.domain_specific_kpis,
            "domain_mode": self.domain_mode,
            "root_causes": self.root_causes,
            "visualization_rules": self.visualization_rules,
            "language_policy": self.language_policy,
            "executive_summary_style": self.executive_summary_style,
            "recommended_questions": self.recommended_questions,
            "rag_context": self.rag_context,
            "industry": self.industry,
            "knowledge_pack_id": self.knowledge_pack_id,
            "benchmark_provider": self.benchmark_provider,
            "glossary_provider": self.glossary_provider,
            "executive_guidance_provider": self.executive_guidance_provider,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> DomainContext:
        safe = payload or {}
        nested = safe.get("domain_context") or {}
        detection = safe.get("detection") or {}
        domain_detector = safe.get("domain_detector") or {}
        business_context_engine = safe.get("business_context_engine") or {}

        detected_domain = (
            nested.get("detected_domain")
            or domain_detector.get("detected_domain")
            or detection.get("domain")
            or "Generic Business Dataset"
        )
        confidence = (
            nested.get("confidence")
            or domain_detector.get("confidence")
            or detection.get("confidence")
            or "low"
        )
        confidence_score = float(
            nested.get("confidence_score")
            or domain_detector.get("confidence_score")
            or detection.get("confidence_score")
            or 0.0
        )
        business_context = (
            nested.get("business_context")
            or business_context_engine.get("business_context")
            or detection.get("business_context")
            or "General business analytics and evidence-based decision support."
        )

        return cls(
            detected_domain=str(detected_domain),
            confidence=str(confidence),
            confidence_score=confidence_score,
            business_context=str(business_context),
            industry=str(nested.get("industry") or detected_domain),
            domain_specific_kpis=list(nested.get("domain_specific_kpis") or safe.get("domain_kpis") or []),
            storyboard_template=dict(nested.get("storyboard_template") or safe.get("dynamic_storyboard_template") or {}),
            dashboard_template=dict(nested.get("dashboard_template") or safe.get("dynamic_dashboard_template") or {}),
            visualization_rules=dict(nested.get("visualization_rules") or safe.get("visualization_rules") or {}),
            language_policy=dict(nested.get("language_policy") or safe.get("language_policy") or {}),
            executive_summary_style=dict(nested.get("executive_summary_style") or safe.get("executive_summary_style") or {}),
            recommended_questions=list(nested.get("recommended_questions") or safe.get("recommended_questions") or []),
            rag_context=dict(nested.get("rag_context") or safe.get("rag_context") or {}),
            knowledge_pack_id=(nested.get("knowledge_pack_id") or safe.get("knowledge_pack_id")),
            benchmark_provider=(nested.get("benchmark_provider") or safe.get("benchmark_provider")),
            glossary_provider=(nested.get("glossary_provider") or safe.get("glossary_provider")),
            executive_guidance_provider=(nested.get("executive_guidance_provider") or safe.get("executive_guidance_provider")),
            detection_signals=list(domain_detector.get("signals") or detection.get("signals") or []),
            dataset_classifier=dict(safe.get("dataset_classifier") or {}),
            business_context_engine=dict(business_context_engine),
            root_causes=list(safe.get("root_causes") or []),
            domain_mode=dict(safe.get("domain_mode") or {}),
        )
