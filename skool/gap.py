"""
Gap analysis: compare scan data against full Skool feature set.
Returns prioritized list of features with status, impact, and recommendations.
Mirrors the Step 12 table in ~/.claude/skills/skool-scan/SKILL.md
"""

# Full 21-feature matrix
FEATURES = [
    {
        "name": "Membership Questions",
        "key": "plugins.Membership questions",
        "impact": "high",
        "missing_action": "Collect contact info + qualify new members on join",
    },
    {
        "name": "Auto DM",
        "key": "plugins.Auto DM new members",
        "impact": "med",
        "missing_action": "Welcome new members with onboarding link",
    },
    {
        "name": "Onboarding Video",
        "key": "plugins.Onboarding video",
        "impact": "med",
        "missing_action": "First impression video for new members",
    },
    {
        "name": "Meta Pixel",
        "key": "plugins.Meta pixel tracking",
        "impact": "med",
        "missing_action": "Track conversions and retarget visitors",
    },
    {
        "name": "Google Ads Tracking",
        "key": "plugins.Google ads tracking",
        "impact": "med",
        "missing_action": "Optimize ad spend with conversion tracking",
    },
    {
        "name": "Cancellation Video",
        "key": "plugins.Cancellation video",
        "impact": "high",
        "missing_action": "Retain members with personal video on cancel page",
    },
    {
        "name": "Unlock Posting",
        "key": "plugins.Unlock posting",
        "impact": "low",
        "missing_action": "Gate posting behind level to reduce noise",
    },
    {
        "name": "Instant Approval",
        "key": "plugins.Instant approval",
        "impact": "low",
        "missing_action": "Auto-approve membership for frictionless onboarding",
    },
    {
        "name": "Webhook",
        "key": "plugins.Webhook",
        "impact": "low",
        "missing_action": "Integrate with external systems",
    },
    {
        "name": "Hyros Tracking",
        "key": "plugins.Hyros tracking",
        "impact": "low",
        "missing_action": "Advanced ad attribution",
    },
    {
        "name": "Affiliate Program",
        "key": "settings.affiliates",
        "impact": "high",
        "missing_action": "Incentivize members to refer others",
    },
    {
        "name": "Zapier Integration",
        "key": "plugins.Zapier integration",
        "impact": "med",
        "missing_action": "Automate CRM sync, email lists, notifications",
    },
    {
        "name": "Skool Call",
        "key": "calendar.uses_skool_call",
        "impact": "med",
        "missing_action": "Native calls auto-post replays in community",
    },
    {
        "name": "Map",
        "key": "map.enabled",
        "impact": "low",
        "missing_action": "Enable for member networking and local meetups",
    },
    {
        "name": "Custom Level Names",
        "key": "leaderboards.custom_levels",
        "impact": "med",
        "missing_action": "Brand levels to match community identity",
    },
    {
        "name": "Course Unlock Levels",
        "key": "_course_unlock_levels",
        "impact": "med",
        "missing_action": "Gate courses behind levels to incentivize engagement",
    },
    {
        "name": "Drip Content",
        "key": "_drip_content",
        "impact": "low",
        "missing_action": "Time-gate content to prevent overwhelm",
    },
    {
        "name": "Community Rules",
        "key": "_has_rules",
        "impact": "med",
        "missing_action": "Set expectations and reduce moderation load",
    },
    {
        "name": "Video in Courses",
        "key": "_has_video",
        "impact": "high",
        "missing_action": "Add video to increase engagement and completion",
    },
    {
        "name": "Course Completion",
        "key": "_has_completion",
        "impact": "high",
        "missing_action": "0% = content isn't being consumed - check course structure",
    },
    {
        "name": "Conversion Rate",
        "key": "_has_conversion",
        "impact": "high",
        "missing_action": "0% conversion = about page needs work",
    },
]


def _resolve(data: dict, key: str):
    """Resolve a dotted key path or computed key (_prefixed) from scan data."""
    if key == "_course_unlock_levels":
        courses = data.get("classroom", {}).get("courses", [])
        return any(c.get("unlock", "Open") not in ("Open", "open", None) for c in courses)

    if key == "_drip_content":
        # Not extractable from current scanner - report as False (not detected)
        return False

    if key == "_has_rules":
        rules = data.get("community", {}).get("rules", [])
        return len(rules) > 0

    if key == "_has_video":
        return data.get("classroom", {}).get("video_count", 0) > 0

    if key == "_has_completion":
        # Not extractable from current scanner (all 0%) - report as False
        return False

    if key == "_has_conversion":
        return data.get("dashboard", {}).get("conversion_rate", 0.0) > 0.0

    # Dotted key: supports plugins.*, settings.*, calendar.*, map.*, leaderboards.*
    parts = key.split(".", 1)
    top = parts[0]

    if top == "plugins":
        return data.get("settings", {}).get("plugins", {}).get(parts[1])

    if top == "settings":
        return data.get("settings", {}).get(parts[1])

    cur = data
    for p in parts:
        cur = cur.get(p) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def analyze(data: dict) -> list:
    """
    Returns list of assessment dicts:
    {feature, status, impact, action}
    - status: "Using" or "Not using"
    - impact: "high" / "med" / "low"  (low when already using)
    - action: recommendation string (empty when already using)
    """
    results = []
    for f in FEATURES:
        val = _resolve(data, f["key"])
        using = bool(val)
        results.append(
            {
                "feature": f["name"],
                "status": "Using" if using else "Not using",
                "impact": "low" if using else f["impact"],
                "action": "" if using else f["missing_action"],
            }
        )
    return results
