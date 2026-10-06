import urllib.parse
from typing import Any, Dict, List, Optional
from app.engines.audience.contracts import UTMBuilderRequest, UTMBuilderResponse


class AudienceAnalyzer:
    """Core analytical logic for owned audience economics, UTM link generation, and attribution."""

    def __init__(self, rules: Dict[str, Any]):
        self.rules = rules or {}

    def build_utm_tracking_url(
        self,
        request: UTMBuilderRequest,
        magnet_title: Optional[str] = None,
        cta_copy: Optional[str] = None,
    ) -> UTMBuilderResponse:
        """Constructs a fully tracked UTM destination URL with standardized parameter tagging."""
        platform = request.platform.lower().strip()
        medium_mapping = self.rules.get("utm_defaults", {}).get("medium_mapping", {})
        
        # Determine utm_medium
        utm_medium = request.custom_medium or medium_mapping.get(platform, "social_referral")
        utm_source = platform
        
        # Determine utm_campaign
        prefix = self.rules.get("utm_defaults", {}).get("campaign_prefix", "sc_")
        if request.campaign_name:
            utm_campaign = f"{prefix}{request.campaign_name}"
        elif request.lead_magnet_slug:
            utm_campaign = f"{prefix}{request.lead_magnet_slug}"
        else:
            utm_campaign = f"{prefix}general"

        utm_content = request.content_slug

        # Parse base_url and merge query params
        parsed = urllib.parse.urlparse(request.base_url)
        existing_params = dict(urllib.parse.parse_qsl(parsed.query))
        
        existing_params["utm_source"] = utm_source
        existing_params["utm_medium"] = utm_medium
        existing_params["utm_campaign"] = utm_campaign
        if utm_content:
            existing_params["utm_content"] = utm_content

        new_query = urllib.parse.urlencode(existing_params)
        tracking_url = urllib.parse.urlunparse((
            parsed.scheme or "https",
            parsed.netloc or parsed.path,
            parsed.path if parsed.netloc else "",
            parsed.params,
            new_query,
            parsed.fragment,
        ))

        # Markdown formatted link
        display_text = magnet_title or "Get the Free Resource"
        markdown_link = f"[{display_text}]({tracking_url})"

        # Ready to paste CTA snippet
        cta_text = cta_copy or f"Get the free companion resource here: {tracking_url}"
        if "{url}" in cta_text:
            copy_paste_cta = cta_text.replace("{url}", tracking_url)
        else:
            copy_paste_cta = f"{cta_text}\n👉 {tracking_url}"

        return UTMBuilderResponse(
            tracking_url=tracking_url,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            formatted_markdown_link=markdown_link,
            copy_paste_cta=copy_paste_cta,
        )

    def calculate_conversion_metrics(
        self,
        clicks: int,
        signups: int,
        customers: int = 0,
        revenue_usd: float = 0.0,
        estimated_value_usd: float = 15.0,
    ) -> Dict[str, Any]:
        """Calculates conversion percentages and estimated asset valuation."""
        conv_rate = round((signups / clicks * 100), 2) if clicks > 0 else 0.0
        cust_rate = round((customers / signups * 100), 2) if signups > 0 else 0.0
        est_asset_val = round(signups * estimated_value_usd, 2)
        
        target_rate = self.rules.get("target_conversion_rate_pct", 3.0)
        critical_rate = self.rules.get("critical_conversion_rate_pct", 1.0)
        excellent_rate = self.rules.get("excellent_conversion_rate_pct", 5.0)

        if clicks == 0:
            performance_tier = "NO_TRAFFIC"
        elif conv_rate >= excellent_rate:
            performance_tier = "EXCELLENT"
        elif conv_rate >= target_rate:
            performance_tier = "ON_TARGET"
        elif conv_rate < critical_rate:
            performance_tier = "CRITICAL_LOW"
        else:
            performance_tier = "MODERATE"

        return {
            "conversion_rate_pct": conv_rate,
            "customer_conversion_rate_pct": cust_rate,
            "estimated_asset_value_usd": est_asset_val,
            "performance_tier": performance_tier,
        }

    def aggregate_summary(
        self,
        magnets: List[Dict[str, Any]],
        conversions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Aggregates all audience data into studio-level KPIs."""
        total_lead_magnets = len(magnets)
        active_magnets = sum(1 for m in magnets if m.get("status") == "ACTIVE")
        
        total_clicks = sum(c.get("clicks", 0) for c in conversions)
        total_signups = sum(c.get("signups", 0) for c in conversions)
        total_customers = sum(c.get("customers", 0) for c in conversions)
        total_revenue_usd = round(sum(c.get("revenue_usd", 0.0) for c in conversions), 2)

        overall_conv_rate = round((total_signups / total_clicks * 100), 2) if total_clicks > 0 else 0.0

        # Magnet maps and valuations
        magnet_map: Dict[str, Dict[str, Any]] = {m["id"]: m for m in magnets if "id" in m}
        
        by_magnet_type: Dict[str, int] = {}
        for m in magnets:
            m_type = m.get("magnet_type", "cheat_sheet")
            by_magnet_type[m_type] = by_magnet_type.get(m_type, 0) + 1

        by_platform: Dict[str, Dict[str, Any]] = {}
        for c in conversions:
            p = c.get("platform", "direct").lower()
            if p not in by_platform:
                by_platform[p] = {
                    "clicks": 0,
                    "signups": 0,
                    "customers": 0,
                    "revenue_usd": 0.0,
                    "conversion_rate_pct": 0.0,
                }
            by_platform[p]["clicks"] += c.get("clicks", 0)
            by_platform[p]["signups"] += c.get("signups", 0)
            by_platform[p]["customers"] += c.get("customers", 0)
            by_platform[p]["revenue_usd"] = round(by_platform[p]["revenue_usd"] + c.get("revenue_usd", 0.0), 2)

        for p_data in by_platform.values():
            if p_data["clicks"] > 0:
                p_data["conversion_rate_pct"] = round((p_data["signups"] / p_data["clicks"] * 100), 2)

        # Calculate estimated total list value based on per-magnet value or default
        estimated_total_list_value = 0.0
        default_val = self.rules.get("default_lead_value_usd", 15.0)

        magnet_signups: Dict[str, int] = {}
        magnet_clicks: Dict[str, int] = {}
        for c in conversions:
            mid = c.get("lead_magnet_id")
            if mid:
                magnet_signups[mid] = magnet_signups.get(mid, 0) + c.get("signups", 0)
                magnet_clicks[mid] = magnet_clicks.get(mid, 0) + c.get("clicks", 0)

        top_performing_magnets = []
        for mid, m in magnet_map.items():
            s = magnet_signups.get(mid, 0)
            cl = magnet_clicks.get(mid, 0)
            val_per_lead = m.get("estimated_value_usd", default_val)
            magnet_asset_val = round(s * val_per_lead, 2)
            estimated_total_list_value += magnet_asset_val
            c_rate = round((s / cl * 100), 2) if cl > 0 else 0.0
            
            top_performing_magnets.append({
                "id": mid,
                "title": m.get("title", ""),
                "slug": m.get("slug", ""),
                "magnet_type": m.get("magnet_type", ""),
                "clicks": cl,
                "signups": s,
                "conversion_rate_pct": c_rate,
                "estimated_asset_value_usd": magnet_asset_val,
            })

        top_performing_magnets.sort(key=lambda x: x["signups"], reverse=True)

        return {
            "total_lead_magnets": total_lead_magnets,
            "active_magnets": active_magnets,
            "total_clicks": total_clicks,
            "total_signups": total_signups,
            "total_customers": total_customers,
            "total_revenue_usd": total_revenue_usd,
            "overall_conversion_rate_pct": overall_conv_rate,
            "estimated_total_list_value_usd": round(estimated_total_list_value, 2),
            "by_magnet_type": by_magnet_type,
            "by_platform": by_platform,
            "top_performing_magnets": top_performing_magnets[:5],
        }
