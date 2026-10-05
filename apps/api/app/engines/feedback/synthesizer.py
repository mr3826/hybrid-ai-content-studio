from typing import Any, Dict, List, Optional
import uuid


class FeedbackSynthesizer:
    """Synthesizes actionable creator feedback lessons from publication snapshots and content data."""

    def __init__(self, rules: Dict[str, Any]):
        self.rules = rules
        self.hook_critical = float(rules.get("hook_retention_critical_threshold_pct", 45.0))
        self.hook_viral = float(rules.get("hook_retention_viral_threshold_pct", 75.0))
        self.eng_critical = float(rules.get("engagement_rate_critical_threshold_pct", 2.0))
        self.eng_strong = float(rules.get("engagement_rate_strong_threshold_pct", 8.0))
        self.min_impressions = int(rules.get("min_impressions_for_evaluation", 50))

    def evaluate_item_performance(
        self,
        snapshot: Dict[str, Any],
        content_item: Optional[Dict[str, Any]] = None,
        script_data: Optional[Dict[str, Any]] = None,
        brand_profile: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate a single publication snapshot against thresholds and return candidate lesson proposals."""
        views = int(snapshot.get("views", 0))
        impressions = int(snapshot.get("impressions", 0))
        platform = snapshot.get("platform", "unknown")
        item_id = snapshot.get("content_item_id")
        item_title = (content_item or {}).get("working_title", "Untitled Content")

        lessons: List[Dict[str, Any]] = []

        # 1. 3-Second Hook Retention Evaluation
        hook_3s = snapshot.get("hook_retention_3s_pct")
        if hook_3s is not None and views >= 10:
            hook_text = (script_data or {}).get("hook_text", "")
            
            if hook_3s < self.hook_critical:
                # Weak hook drop
                banned_candidate = None
                cliches = ["hey guys", "welcome back", "in this video", "today i'm going to", "what's up"]
                for c in cliches:
                    if hook_text and c in hook_text.lower():
                        banned_candidate = c
                        break

                if banned_candidate:
                    lessons.append({
                        "id": str(uuid.uuid4()),
                        "content_item_id": item_id,
                        "lesson_type": "banned_phrase_addition",
                        "title": f"Ban Opening Cliché '{banned_candidate}' on {platform.title()}",
                        "observation": f"3-second hook retention dropped to {hook_3s:.1f}% (below {self.hook_critical}% threshold) on {platform.title()} with opening line containing '{banned_candidate}'.",
                        "impact_level": "HIGH",
                        "confidence_score": 0.88,
                        "evidence_data": {
                            "platform": platform,
                            "views": views,
                            "hook_retention_3s_pct": hook_3s,
                            "hook_text": hook_text,
                            "identified_cliche": banned_candidate,
                        },
                        "proposed_adjustment": {
                            "target": "brand_profile",
                            "field": "avoid_vocabulary",
                            "action": "append",
                            "value": banned_candidate,
                            "summary": f"Add '{banned_candidate}' to Brand Avoid Vocabulary to stop viewer dropoff."
                        },
                        "status": "PENDING",
                    })
                else:
                    lessons.append({
                        "id": str(uuid.uuid4()),
                        "content_item_id": item_id,
                        "lesson_type": "hook_optimization",
                        "title": f"Tighten Opening Pacing for {platform.title()} ({hook_3s:.1f}% 3s Retention)",
                        "observation": f"3-second hook retention was {hook_3s:.1f}% on {platform.title()}, indicating viewers scrolled away before the core payoff.",
                        "impact_level": "HIGH",
                        "confidence_score": 0.82,
                        "evidence_data": {
                            "platform": platform,
                            "views": views,
                            "hook_retention_3s_pct": hook_3s,
                            "hook_text": hook_text,
                        },
                        "proposed_adjustment": {
                            "target": "brand_memory",
                            "field": "hook_pattern",
                            "action": "record_memory",
                            "value": f"Avoid slow preamble on {platform.title()}. Deliver primary visual proof within the first 1.5 seconds.",
                            "summary": f"Record hook pacing constraint for {platform.title()} into Brand Memory."
                        },
                        "status": "PENDING",
                    })

            elif hook_3s >= self.hook_viral:
                # Viral hook retention!
                lessons.append({
                    "id": str(uuid.uuid4()),
                    "content_item_id": item_id,
                    "lesson_type": "hook_optimization",
                    "title": f"Promote Top Performing Hook to Brand Exemplars ({hook_3s:.1f}% on {platform.title()})",
                    "observation": f"Viral 3-second hook retention of {hook_3s:.1f}% achieved on {platform.title()} with title '{item_title}'.",
                    "impact_level": "MEDIUM",
                    "confidence_score": 0.92,
                    "evidence_data": {
                        "platform": platform,
                        "views": views,
                        "hook_retention_3s_pct": hook_3s,
                        "hook_text": hook_text,
                    },
                    "proposed_adjustment": {
                        "target": "brand_exemplar",
                        "field": "approved_hook",
                        "action": "add_exemplar",
                        "value": {
                            "category": "approved_hook",
                            "title": f"Top Hook: {item_title[:40]}",
                            "content": hook_text or item_title,
                            "platform": platform,
                            "context_note": f"Achieved {hook_3s:.1f}% 3s retention on {platform.title()}",
                        },
                        "summary": f"Add '{hook_text or item_title}' to Brand Exemplars as a proven winning hook pattern."
                    },
                    "status": "PENDING",
                })

        # 2. Engagement Rate Evaluation
        likes = int(snapshot.get("likes", 0))
        comments = int(snapshot.get("comments", 0))
        shares = int(snapshot.get("shares", 0))
        saves = int(snapshot.get("saves", 0))
        total_eng = likes + comments + shares + saves

        if views >= 20:
            eng_rate = (total_eng / views) * 100.0
            if eng_rate < self.eng_critical:
                lessons.append({
                    "id": str(uuid.uuid4()),
                    "content_item_id": item_id,
                    "lesson_type": "cta_refinement",
                    "title": f"Refine Call-To-Action (Engagement Rate {eng_rate:.1f}% on {platform.title()})",
                    "observation": f"Engagement rate is critically low at {eng_rate:.1f}% (benchmark >= {self.eng_critical}%). Viewers consumed content without interacting.",
                    "impact_level": "MEDIUM",
                    "confidence_score": 0.78,
                    "evidence_data": {
                        "platform": platform,
                        "views": views,
                        "engagement_rate_pct": eng_rate,
                        "total_interactions": total_eng,
                    },
                    "proposed_adjustment": {
                        "target": "brand_profile",
                        "field": "cta_style",
                        "action": "update",
                        "value": "Switch from passive requests to interactive question-based CTA asking audience for specific experience.",
                        "summary": "Update Brand CTA style from passive request to interactive inquiry."
                    },
                    "status": "PENDING",
                })
            elif eng_rate >= self.eng_strong:
                lessons.append({
                    "id": str(uuid.uuid4()),
                    "content_item_id": item_id,
                    "lesson_type": "topic_reinforcement",
                    "title": f"Reinforce High-Affinity Topic ({eng_rate:.1f}% Engagement on {platform.title()})",
                    "observation": f"Exceptional audience engagement of {eng_rate:.1f}% achieved on topic '{item_title}'.",
                    "impact_level": "HIGH",
                    "confidence_score": 0.89,
                    "evidence_data": {
                        "platform": platform,
                        "views": views,
                        "engagement_rate_pct": eng_rate,
                        "total_interactions": total_eng,
                    },
                    "proposed_adjustment": {
                        "target": "brand_memory",
                        "field": "topic",
                        "action": "record_memory",
                        "value": f"Prioritize future deep-dives on '{item_title}' due to {eng_rate:.1f}% audience engagement.",
                        "summary": f"Record high audience interest in '{item_title}' into Brand Memory for future opportunity prioritization."
                    },
                    "status": "PENDING",
                })

        # 3. Retention Rate & Pacing Evaluation
        retention = snapshot.get("retention_rate_pct")
        if retention is not None and views >= 20 and retention < 30.0:
            lessons.append({
                "id": str(uuid.uuid4()),
                "content_item_id": item_id,
                "lesson_type": "pacing_adjustment",
                "title": f"Improve Mid-Video Retention ({retention:.1f}% on {platform.title()})",
                "observation": f"Average retention dropped to {retention:.1f}% before the conclusion, indicating mid-video pacing drag.",
                "impact_level": "MEDIUM",
                "confidence_score": 0.80,
                "evidence_data": {
                    "platform": platform,
                    "views": views,
                    "retention_rate_pct": retention,
                },
                "proposed_adjustment": {
                    "target": "brand_memory",
                    "field": "visual_pattern",
                    "action": "record_memory",
                    "value": "Inject pattern interrupt (text callout or evidence graph) every 8-10 seconds.",
                    "summary": "Record pattern interrupt guideline into Brand Memory to retain mid-video audience."
                },
                "status": "PENDING",
            })

        return lessons
