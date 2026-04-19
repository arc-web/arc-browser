"""
HTML report generator for Skool group audits.
Takes structured scan data and produces a styled standalone HTML file.
"""
import os
from datetime import date
from pathlib import Path

from .gap import analyze as gap_analyze

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def generate_report(data: dict, output_path: str = None) -> str:
    """
    Generate an HTML audit report from scan data.

    Args:
        data: The scanner.data dict with all collected findings
        output_path: Where to write the HTML file. Defaults to ~/<slug>-audit.html

    Returns:
        Path to the generated HTML file
    """
    slug = data.get("slug", "unknown")
    if not output_path:
        output_path = os.path.expanduser(f"~/{slug}-audit.html")

    css = _get_css()
    body = _build_body(data)
    group_name = data.get("about", {}).get("groupName", slug)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{group_name} - Skool Audit Report</title>
<style>{css}</style>
</head>
<body>
<div class="container">
{body}
<div style="text-align:center;padding:2rem;color:var(--text-dim);font-size:0.8rem">
  {group_name} Skool Audit - Generated {date.today().isoformat()}<br>
  Data collected via admin access to skool.com/{slug}
</div>
</div>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)

    return output_path


def _get_css() -> str:
    css_file = TEMPLATE_DIR / "report.css"
    if css_file.exists():
        return css_file.read_text()
    return _INLINE_CSS


def _build_body(data: dict) -> str:
    return "\n".join([
        _section_header(data),
        _section_stats(data),
        _section_overview(data),
        _section_community(data),
        _section_classroom(data),
        _section_calendar_map(data),
        _section_leaderboards(data),
        _section_plugins(data),
        _section_gap_analysis(data),
        _section_action_items(data),
    ])


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_header(data: dict) -> str:
    slug = data.get("slug", "unknown")
    group_name = data.get("about", {}).get("groupName", slug)
    return f"""
<div class="header">
  <h1>{group_name}</h1>
  <div class="subtitle">Comprehensive Skool Group Audit Report</div>
  <div class="date">Audit Date: {date.today().isoformat()} &mdash; skool.com/{slug}</div>
</div>"""


def _section_stats(data: dict) -> str:
    about = data.get("about", {})
    dashboard = data.get("dashboard", {})
    classroom = data.get("classroom", {})
    community = data.get("community", {})
    calendar = data.get("calendar", {})

    members = about.get("members", "—")
    mrr = dashboard.get("mrr", "—")
    mrr_str = f"${mrr:,}" if isinstance(mrr, (int, float)) else str(mrr)
    engagement = dashboard.get("engagement", "—")
    engagement_str = f"{engagement}%" if isinstance(engagement, (int, float)) else str(engagement)
    retention = dashboard.get("retention", "—")
    retention_str = f"{retention}%" if isinstance(retention, (int, float)) else str(retention)
    courses = classroom.get("course_count", "—")
    posts = community.get("total_posts", "—")
    events = len(calendar.get("events", []))
    price = about.get("pricing", "—")

    def card(value, label):
        return f"""  <div class="stat-card">
    <div class="value">{value}</div>
    <div class="label">{label}</div>
  </div>"""

    cards = "\n".join([
        card(members, "Members"),
        card(mrr_str, "MRR"),
        card(engagement_str, "Engagement"),
        card(retention_str, "Retention"),
        card(courses, "Courses"),
        card(posts, "Posts"),
        card(events, "Weekly Events"),
        card(price, "Price"),
    ])
    return f'<div class="stats-grid">\n{cards}\n</div>'


def _section_overview(data: dict) -> str:
    about = data.get("about", {})
    dashboard = data.get("dashboard", {})
    members_data = data.get("members", {})
    settings = data.get("settings", {})

    privacy = about.get("privacy", "—")
    creator = about.get("creator", "—")
    pricing = about.get("pricing", "—")
    trial = settings.get("trial_days")
    trial_str = f"{trial}-day trial" if trial else "No trial"
    pricing_model = settings.get("pricing_model", "—")
    admins_count = about.get("admins", "—")

    overview_rows = [
        ("Privacy", privacy),
        ("Creator", creator),
        ("Pricing", f"{pricing} ({pricing_model})"),
        ("Trial", trial_str),
        ("Admins", str(admins_count)),
        ("Active Members", members_data.get("active", "—")),
        ("Visitors (30d)", str(dashboard.get("visitors_30d", "—"))),
        ("Signups (30d)", str(dashboard.get("signups_30d", "—"))),
        ("Conversion", f"{dashboard.get('conversion_rate', 0):.1f}%"),
    ]

    rows_html = "\n".join(
        f"<tr><td style='color:var(--text-dim)'>{k}</td><td>{v}</td></tr>"
        for k, v in overview_rows
    )

    traffic = dashboard.get("traffic", {})
    traffic_bars = ""
    for source, pct in sorted(traffic.items(), key=lambda x: -x[1]):
        traffic_bars += f"""
  <div style="margin-bottom:0.6rem">
    <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:0.25rem">
      <span>{source}</span><span style="color:var(--text-dim)">{pct}%</span>
    </div>
    <div style="background:var(--surface-2);border-radius:4px;height:6px">
      <div style="width:{pct}%;background:var(--accent);height:6px;border-radius:4px"></div>
    </div>
  </div>"""

    return f"""
<div class="two-col" style="margin-bottom:1.5rem">
  <div class="section">
    <h2>Group Overview</h2>
    <table><tbody>{rows_html}</tbody></table>
  </div>
  <div class="section">
    <h2>Traffic Sources (30d)</h2>
    {traffic_bars if traffic_bars else '<p style="color:var(--text-dim)">No traffic data</p>'}
  </div>
</div>"""


def _section_community(data: dict) -> str:
    community = data.get("community", {})
    categories = community.get("categories", [])
    rules = community.get("rules", [])
    pinned = community.get("pinned_posts", [])
    total_posts = community.get("total_posts", 0)
    zero_reply = community.get("zero_reply_posts", 0)
    unanswered = community.get("unanswered_member_posts", 0)

    def _cat_row(c):
        if isinstance(c, str):
            return f"<tr><td>{c}</td><td style='color:var(--text-dim)'>—</td><td style='color:var(--text-dim)'>—</td></tr>"
        return f"<tr><td>{c.get('name','')}</td><td style='color:var(--text-dim)'>{c.get('permissions','')}</td><td style='color:var(--text-dim)'>{c.get('sort','')}</td></tr>"
    cat_rows = "\n".join(_cat_row(c) for c in categories) if categories else "<tr><td colspan='3' style='color:var(--text-dim)'>No categories found</td></tr>"

    pinned_list = "".join(
        f"<li style='padding:0.3rem 0;border-top:1px solid var(--border)'><strong>{p.get('title','')}</strong> <span style='color:var(--text-dim);font-size:0.8rem'>by {p.get('author','')}</span></li>"
        for p in pinned
    ) if pinned else "<li style='color:var(--text-dim)'>No pinned posts</li>"

    rules_list = "".join(
        f"<li style='padding:0.25rem 0'>{i+1}. {r}</li>"
        for i, r in enumerate(rules)
    ) if rules else "<li style='color:var(--text-dim)'>No rules configured</li>"

    return f"""
<div class="section" style="margin-bottom:1.5rem">
  <h2>Community</h2>
  <div class="two-col">
    <div>
      <h3>Categories</h3>
      <table>
        <thead><tr><th>Name</th><th>Post Access</th><th>Sort</th></tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>
      <h3 style="margin-top:1rem">Pinned Posts</h3>
      <ul style="list-style:none;padding:0">{pinned_list}</ul>
    </div>
    <div>
      <h3>Post Stats</h3>
      <table><tbody>
        <tr><td style='color:var(--text-dim)'>Total Posts</td><td>{total_posts}</td></tr>
        <tr><td style='color:var(--text-dim)'>Zero Reply Posts</td><td>{zero_reply}</td></tr>
        <tr><td style='color:var(--text-dim)'>Unanswered Member Posts</td>
          <td><span class="badge {'badge-off' if unanswered > 0 else 'badge-on'}">{unanswered}</span></td></tr>
      </tbody></table>
      <h3 style="margin-top:1rem">Community Rules ({len(rules)})</h3>
      <ul style="list-style:none;padding:0;font-size:0.9rem">{rules_list}</ul>
    </div>
  </div>
</div>"""


def _section_classroom(data: dict) -> str:
    classroom = data.get("classroom", {})
    raw_courses = classroom.get("courses", [])
    courses = sorted(raw_courses, key=lambda c: -(c.get("lessonCount") or len(c.get("lessons", [])) if isinstance(c.get("lessons"), list) else c.get("lessonCount", 0)))
    total_lessons = classroom.get("total_lessons") or sum(c.get("lessonCount", 0) for c in courses)
    video_count = classroom.get("video_count") or sum(1 for c in courses if c.get("hasVideo"))

    depth_badge = {
        "Rich": "badge-rich",
        "Moderate": "badge-moderate",
        "Minimal": "badge-minimal",
        "Light": "badge-minimal",
        "Empty": "badge-empty",
    }

    unlock_badge = {
        "Open": "badge-open",
    }

    rows = ""
    for c in courses:
        depth = c.get("depth", "—")
        unlock = c.get("unlock", "Open")
        dbadge = depth_badge.get(depth, "badge-empty")
        ubadge = unlock_badge.get(unlock, "badge-locked")
        lesson_count = c.get("lessonCount") or (len(c.get("lessons", [])) if isinstance(c.get("lessons"), list) else 0)
        course_name = c.get("courseName") or c.get("name", "")
        rows += f"""<tr>
  <td>{course_name}</td>
  <td style="text-align:center">{lesson_count}</td>
  <td><span class="badge {ubadge}">{unlock}</span></td>
  <td><span class="badge {dbadge}">{depth}</span></td>
  <td style="color:var(--text-dim);font-size:0.85rem">{c.get('topics','')}</td>
</tr>"""

    summary = f"""<tr style="background:var(--surface-2)">
  <td><strong>Total</strong></td>
  <td style="text-align:center"><strong>{total_lessons}</strong></td>
  <td colspan="2" style="color:var(--text-dim)">{len(courses)} courses, {video_count} with video</td>
  <td></td>
</tr>"""

    return f"""
<div class="section" style="margin-bottom:1.5rem">
  <h2>Classroom ({len(courses)} Courses)</h2>
  <table>
    <thead><tr><th>Course</th><th style="text-align:center">Lessons</th><th>Unlock</th><th>Content Depth</th><th>Key Topics</th></tr></thead>
    <tbody>{rows}{summary}</tbody>
  </table>
</div>"""


def _section_calendar_map(data: dict) -> str:
    calendar = data.get("calendar", {})
    map_data = data.get("map", {})

    events = calendar.get("events", [])
    uses_skool_call = calendar.get("uses_skool_call", False)
    uses_zoom = calendar.get("uses_zoom", False)
    call_type = "Skool Call" if uses_skool_call else ("Zoom" if uses_zoom else "Unknown")
    call_badge = "badge-on" if uses_skool_call else "badge-off"

    event_rows = "\n".join(
        f"<tr><td>{e.get('name','')}</td><td style='color:var(--text-dim)'>{e.get('day','')}</td><td style='color:var(--text-dim)'>{e.get('time','')}</td></tr>"
        for e in events
    ) if events else "<tr><td colspan='3' style='color:var(--text-dim)'>No events found</td></tr>"

    map_enabled = map_data.get("enabled", False)
    pins = map_data.get("pins", 0)
    map_badge = "badge-on" if map_enabled else "badge-off"
    map_status = "Enabled" if map_enabled else "Disabled"

    return f"""
<div class="two-col" style="margin-bottom:1.5rem">
  <div class="section">
    <h2>Calendar ({len(events)} Events)</h2>
    <table>
      <thead><tr><th>Event</th><th>Day</th><th>Time</th></tr></thead>
      <tbody>{event_rows}</tbody>
    </table>
    <div style="margin-top:0.75rem;font-size:0.85rem">
      Call Platform: <span class="badge {call_badge}">{call_type}</span>
    </div>
  </div>
  <div class="section">
    <h2>Map</h2>
    <div style="text-align:center;padding:1.5rem 0">
      <span class="badge {map_badge}" style="font-size:1rem;padding:0.4rem 1rem">{map_status}</span>
      <div style="margin-top:1rem;font-size:2rem;font-weight:700;color:var(--accent-light)">{pins}</div>
      <div style="color:var(--text-dim);font-size:0.85rem">Member Pins</div>
    </div>
  </div>
</div>"""


def _section_leaderboards(data: dict) -> str:
    lb = data.get("leaderboards", {})
    level_dist = lb.get("level_distribution", {})
    top10 = lb.get("all_time_top10", [])
    custom_levels = lb.get("custom_levels", False)
    seven_day_empty = lb.get("seven_day_empty", True)

    level_bars = ""
    max_pct = max(level_dist.values()) if level_dist else 1
    for lvl in range(1, 10):
        pct = level_dist.get(str(lvl), 0)
        bar_width = (pct / max_pct * 100) if max_pct > 0 else 0
        level_bars += f"""
  <div style="margin-bottom:0.5rem">
    <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:0.2rem">
      <span>Level {lvl}</span><span style="color:var(--text-dim)">{pct}%</span>
    </div>
    <div style="background:var(--surface-2);border-radius:4px;height:8px">
      <div style="width:{bar_width:.0f}%;background:var(--accent);height:8px;border-radius:4px"></div>
    </div>
  </div>"""

    top10_rows = "\n".join(
        f"<tr><td style='color:var(--text-dim)'>{m.get('rank','')}</td><td>{m.get('name','')}</td><td style='color:var(--accent-light)'>{m.get('points',0)} pts</td></tr>"
        for m in top10
    ) if top10 else "<tr><td colspan='3' style='color:var(--text-dim)'>No data</td></tr>"

    custom_badge = "badge-on" if custom_levels else "badge-off"
    activity_badge = "badge-off" if seven_day_empty else "badge-on"

    return f"""
<div class="section" style="margin-bottom:1.5rem">
  <h2>Leaderboards</h2>
  <div class="two-col">
    <div>
      <h3>Level Distribution</h3>
      {level_bars}
      <div style="margin-top:0.75rem;font-size:0.85rem">
        Custom Level Names: <span class="badge {custom_badge}">{'Yes' if custom_levels else 'No'}</span>
        &nbsp; 7-Day Activity: <span class="badge {activity_badge}">{'Active' if not seven_day_empty else 'Empty'}</span>
      </div>
    </div>
    <div>
      <h3>All-Time Top 10</h3>
      <table>
        <thead><tr><th>#</th><th>Member</th><th>Points</th></tr></thead>
        <tbody>{top10_rows}</tbody>
      </table>
    </div>
  </div>
</div>"""


def _section_plugins(data: dict) -> str:
    settings = data.get("settings", {})
    plugins = settings.get("plugins", {})
    tabs = settings.get("tabs", {})
    affiliates = settings.get("affiliates", False)
    trial_days = settings.get("trial_days")

    active = [(k, v) for k, v in plugins.items() if v]
    inactive = [(k, v) for k, v in plugins.items() if not v]

    def plugin_list(items, badge_class):
        if not items:
            return '<p style="color:var(--text-dim);font-size:0.85rem">None</p>'
        return "".join(
            f'<div style="margin-bottom:0.4rem"><span class="badge {badge_class}">{("On" if badge_class == "badge-on" else "Off")}</span> {name}</div>'
            for name, _ in items
        )

    tab_rows = "\n".join(
        f"<tr><td>{tab}</td><td><span class='badge {'badge-on' if enabled else 'badge-off'}'>{('Enabled' if enabled else 'Disabled')}</span></td></tr>"
        for tab, enabled in tabs.items()
    )

    return f"""
<div class="section" style="margin-bottom:1.5rem">
  <h2>Plugins &amp; Settings</h2>
  <div class="two-col">
    <div>
      <h3>Active Plugins ({len(active)})</h3>
      {plugin_list(active, 'badge-on')}
    </div>
    <div>
      <h3>Inactive Plugins ({len(inactive)})</h3>
      {plugin_list(inactive, 'badge-off')}
    </div>
  </div>
  <div class="two-col" style="margin-top:1rem">
    <div>
      <h3>Tabs</h3>
      <table><tbody>{tab_rows}</tbody></table>
    </div>
    <div>
      <h3>Other Settings</h3>
      <table><tbody>
        <tr><td style='color:var(--text-dim)'>Affiliates</td>
          <td><span class="badge {'badge-on' if affiliates else 'badge-off'}">{'On' if affiliates else 'Off'}</span></td></tr>
        <tr><td style='color:var(--text-dim)'>Trial Period</td>
          <td>{f'{trial_days} days' if trial_days else 'None'}</td></tr>
        <tr><td style='color:var(--text-dim)'>Pricing Model</td>
          <td>{settings.get('pricing_model', '—')}</td></tr>
      </tbody></table>
    </div>
  </div>
</div>"""


def _section_gap_analysis(data: dict) -> str:
    gap = gap_analyze(data)

    impact_badge = {"high": "badge-high", "med": "badge-med", "low": "badge-low"}

    rows = ""
    for item in gap:
        using = item["status"] == "Using"
        status_badge = "badge-on" if using else "badge-off"
        ibadge = impact_badge.get(item["impact"], "badge-low")
        action = item["action"] if not using else '<span style="color:var(--text-dim)">—</span>'
        rows += f"""<tr>
  <td>{item['feature']}</td>
  <td><span class="badge {status_badge}">{item['status']}</span></td>
  <td><span class="badge {ibadge}">{item['impact'].upper()}</span></td>
  <td style="font-size:0.85rem;color:var(--text-dim)">{action}</td>
</tr>"""

    return f"""
<div class="section" style="margin-bottom:1.5rem">
  <h2>Gap Analysis ({len(gap)} Features)</h2>
  <table>
    <thead><tr><th>Feature</th><th>Status</th><th>Impact</th><th>Assessment / Action</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


def _section_action_items(data: dict) -> str:
    gap = gap_analyze(data)
    not_using = [g for g in gap if g["status"] == "Not using"]

    tiers = {
        "high": [g for g in not_using if g["impact"] == "high"],
        "med": [g for g in not_using if g["impact"] == "med"],
        "low": [g for g in not_using if g["impact"] == "low"],
    }
    tier_labels = {"high": "High Impact", "med": "Medium Impact", "low": "Nice to Have"}

    sections = ""
    for tier, items in tiers.items():
        if not items:
            continue
        label = tier_labels[tier]
        color_map = {"high": "var(--red)", "med": "var(--yellow)", "low": "var(--blue)"}
        color = color_map[tier]
        items_html = ""
        for item in items:
            items_html += f"""
<div class="action-item {tier}">
  <div class="priority"></div>
  <div>
    <div class="text"><strong>{item['feature']}</strong> &mdash; {item['action']}</div>
    <div class="tag">{label}</div>
  </div>
</div>"""
        sections += f"""
  <div>
    <h3 style="color:{color};margin-bottom:0.75rem">{label} ({len(items)})</h3>
    {items_html}
  </div>"""

    if not sections:
        sections = '<p style="color:var(--text-dim)">All features are active. No action items.</p>'

    return f"""
<div class="section" style="margin-bottom:1.5rem">
  <h2>Action Items</h2>
  {sections}
</div>"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_INLINE_CSS = """
:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface-2: #232736;
  --border: #2e3347;
  --text: #e4e6f0;
  --text-dim: #8b8fa7;
  --accent: #6c5ce7;
  --accent-light: #a29bfe;
  --green: #00b894;
  --green-bg: rgba(0,184,148,0.12);
  --yellow: #fdcb6e;
  --yellow-bg: rgba(253,203,110,0.12);
  --red: #ff6b6b;
  --red-bg: rgba(255,107,107,0.12);
  --orange: #e17055;
  --blue: #74b9ff;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem;
}
.container { max-width: 1200px; margin: 0 auto; }
.header {
  text-align: center; padding: 3rem 2rem;
  background: linear-gradient(135deg, var(--surface) 0%, var(--surface-2) 100%);
  border-radius: 16px; border: 1px solid var(--border); margin-bottom: 2rem;
  position: relative; overflow: hidden;
}
.header::before {
  content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
  background: radial-gradient(circle at 30% 50%, rgba(108,92,231,0.08) 0%, transparent 50%);
  pointer-events: none;
}
.header h1 {
  font-size: 2.2rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.5rem;
  background: linear-gradient(135deg, var(--text) 0%, var(--accent-light) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.header .subtitle { color: var(--text-dim); font-size: 1rem; }
.header .date { color: var(--text-dim); font-size: 0.85rem; margin-top: 0.5rem; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
.stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; text-align: center; }
.stat-card .value { font-size: 1.8rem; font-weight: 700; color: var(--accent-light); line-height: 1.2; }
.stat-card .label { font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem; }
.section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.75rem; margin-bottom: 1.5rem; }
.section h2 { font-size: 1.3rem; font-weight: 600; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border); }
.section h3 { font-size: 1rem; font-weight: 600; margin: 1rem 0 0.5rem; color: var(--accent-light); }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th { text-align: left; padding: 0.6rem 0.75rem; background: var(--surface-2); color: var(--text-dim); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
td { padding: 0.6rem 0.75rem; border-top: 1px solid var(--border); }
tr:hover td { background: rgba(108,92,231,0.04); }
.badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.badge-on { background: var(--green-bg); color: var(--green); }
.badge-off { background: var(--red-bg); color: var(--red); }
.badge-high { background: var(--red-bg); color: var(--red); }
.badge-med { background: var(--yellow-bg); color: var(--yellow); }
.badge-low { background: rgba(116,185,255,0.12); color: var(--blue); }
.badge-rich { background: var(--green-bg); color: var(--green); }
.badge-moderate { background: var(--yellow-bg); color: var(--yellow); }
.badge-minimal { background: var(--red-bg); color: var(--red); }
.badge-empty { background: rgba(139,143,167,0.15); color: var(--text-dim); }
.badge-locked { background: rgba(108,92,231,0.15); color: var(--accent-light); }
.badge-open { background: var(--green-bg); color: var(--green); }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
@media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } body { padding: 1rem; } }
.action-item { display: flex; align-items: flex-start; gap: 0.75rem; padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; background: var(--surface-2); }
.action-item .priority { flex-shrink: 0; width: 6px; height: 6px; border-radius: 50%; margin-top: 0.5rem; }
.action-item.high .priority { background: var(--red); box-shadow: 0 0 6px var(--red); }
.action-item.med .priority { background: var(--yellow); box-shadow: 0 0 6px var(--yellow); }
.action-item.low .priority { background: var(--blue); box-shadow: 0 0 6px var(--blue); }
.action-item .text { font-size: 0.9rem; }
.action-item .tag { font-size: 0.7rem; color: var(--text-dim); margin-top: 0.2rem; }
pre { overflow-x: auto; }
"""
