"""
Skool group scanner - extracts structured data from all Skool platform sections.
Each method corresponds to a scan step and returns a dict of findings.
All methods use browser_evaluate via the page object, not browser_navigate directly.
"""
import json
import re


class SkoolScanner:
    """Stateful scanner that collects data from a Skool group."""

    def __init__(self, slug: str):
        self.slug = slug
        self.base = f"https://www.skool.com/{slug}"
        self.data = {
            "slug": slug,
            "about": {},
            "members": {},
            "community": {},
            "classroom": {},
            "calendar": {},
            "map": {},
            "leaderboards": {},
            "settings": {},
            "posts": {},
        }
        self.admin_names = []

    # -- JS snippets executed via page.evaluate() --

    JS_ABOUT = """
    (() => {
      const t = document.body.innerText;
      const grab = label => {
        const re = new RegExp('([\\\\d.,k]+)\\\\s*\\\\n\\\\s*' + label, 'i');
        return (t.match(re) || [])[1] || null;
      };
      const pricing = (t.match(/(\\$[\\d.,]+\\s*\\/\\s*(?:month|year))/i) || t.match(/(Free)/i) || [])[1] || 'unknown';
      const privacy = t.includes('Private') ? 'Private' : t.includes('Public') ? 'Public' : 'unknown';
      const creator = (t.match(/By\\s+([\\w\\s\\u00a0]+?)(?:\\n|$)/i) || [])[1]?.trim() || null;
      return JSON.stringify({
        loggedIn: !t.includes('Log in') && t.includes('Members'),
        groupName: document.title,
        members: grab('Members'), online: grab('Online'),
        admins: grab('Admins?'), pricing, privacy, creator,
      });
    })()
    """

    JS_MEMBERS_SCROLL = """
    (async () => {
      for (let i = 0; i < 20; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 600));
      }
      return 'scrolled';
    })()
    """

    JS_MEMBERS_EXTRACT = """
    (() => {
      const t = document.body.innerText;
      const activeMatch = t.match(/Active\\s*[\\s\\u00a0]*(\\d+)/i);
      const members = [];
      const cards = t.split(/(?=\\d\\n[\\w\\s\\u00a0]+\\n@)/);
      for (const card of cards) {
        const nameMatch = card.match(/([\\w\\s\\u00a0]+)\\n(@[\\w-]+)/);
        if (!nameMatch) continue;
        const name = nameMatch[1].trim();
        const handle = nameMatch[2];
        const isOwner = card.includes('(Owner)');
        const isAdmin = card.includes('(Admin)');
        const isMod = card.includes('(Mod)');
        const role = isOwner ? 'Owner' : isAdmin ? 'Admin' : isMod ? 'Mod' : 'Member';
        members.push({ name, handle, role });
      }
      const admins = members.filter(m => m.role !== 'Member');
      return JSON.stringify({
        active: activeMatch?.[1], totalMembers: members.length,
        admins, adminNames: admins.map(a => a.name), members,
      });
    })()
    """

    JS_CATEGORIES = """
    (() => {
      const t = document.body.innerText;
      const catSection = t.match(/(?:Write something|Go Live)\\n([\\s\\S]*?)(?:Pinned|\\d\\n[\\w\\s\\u00a0]+\\n)/);
      const categories = catSection ? catSection[1].split('\\n').map(s => s.trim()).filter(s => s && s !== 'All' && s.length < 50) : [];
      return JSON.stringify({ categories });
    })()
    """

    JS_CLASSROOM_LIST = """
    (() => {
      const titles = Array.from(document.querySelectorAll('.styled__CourseTitle-sc-ugqan8-12'));
      const courseNames = titles.length > 0
        ? titles.map(t => t.textContent.trim())
        : (() => {
            const body = document.body.innerText;
            const lines = body.split('\\n').map(s => s.trim()).filter(Boolean);
            const courses = [];
            for (let i = 0; i < lines.length; i++) {
              if (lines[i] === '0%' && i > 0 && lines[i-1].length > 1 && lines[i-1].length < 60) {
                courses.push(lines[i-1]);
              }
            }
            return courses;
          })();
      const totalMatch = document.body.innerText.match(/(\\d+)-(\\d+)\\s+of\\s+(\\d+)/);
      return JSON.stringify({
        courseCount: courseNames.length, courseNames,
        total: totalMatch ? parseInt(totalMatch[3]) : courseNames.length,
        selectorWorked: titles.length > 0,
      });
    })()
    """

    @staticmethod
    def js_click_course(index: int) -> str:
        return f"""
        (() => {{
          const titles = Array.from(document.querySelectorAll('.styled__CourseTitle-sc-ugqan8-12'));
          if (titles[{index}]) {{ titles[{index}].click(); return 'clicked ' + titles[{index}].textContent.trim(); }}
          return 'not found at index {index}';
        }})()
        """

    JS_COURSE_DETAIL = """
    (() => {
      const t = document.body.innerText;
      const lines = t.split('\\n').map(s => s.trim()).filter(Boolean);
      const navEnd = lines.findIndex(l => l === '0%');
      let courseName = navEnd > 0 ? lines[navEnd - 1] : 'Unknown';
      const lessons = [];
      const contentStart = lines.findIndex((l, i) => i > navEnd && (l.includes('http') || l.length > 150));
      const end = contentStart > 0 ? contentStart : Math.min(navEnd + 30, lines.length);
      for (let i = navEnd + 1; i < end; i++) {
        const l = lines[i];
        if (l.length > 2 && l.length < 100 && !l.includes('http') && !l.startsWith('Price:') && l !== 'PP' && l !== 'New course') {
          lessons.push(l);
        }
      }
      const unique = [...new Set(lessons)];
      const hasVideo = document.querySelectorAll('video, iframe[src*="youtube"], iframe[src*="vimeo"], iframe[src*="loom"], iframe[src*="wistia"], [class*="video-player"]').length > 0;
      return JSON.stringify({ courseName, lessonCount: unique.length, lessons: unique, hasVideo, url: window.location.href });
    })()
    """

    JS_CALENDAR = """
    (() => {
      const t = document.body.innerText;
      if (t.includes('404') || t.includes("doesn't exist")) return JSON.stringify({ calendarEnabled: false });
      return JSON.stringify({
        calendarEnabled: true,
        hasSkoolCall: t.includes('Skool Call'),
        hasZoom: t.includes('Zoom') || t.includes('zoom.us'),
        rawPreview: t.slice(0, 3000),
      });
    })()
    """

    JS_MAP = """
    (() => {
      const t = document.body.innerText;
      if (t.includes('404') || t.includes("doesn't exist")) return JSON.stringify({ enabled: false });
      const pins = document.querySelectorAll('[class*="pin"], [class*="marker"], [data-testid*="map"]');
      return JSON.stringify({ enabled: true, pinCount: pins.length, bodyPreview: t.slice(0, 500) });
    })()
    """

    JS_LEADERBOARDS = """
    (() => {
      const t = document.body.innerText;
      if (t.includes('404') || t.includes("doesn't exist")) return JSON.stringify({ enabled: false });
      return JSON.stringify({
        enabled: true,
        rawText: t.slice(0, 3000),
        hasCustomLevels: !/Level 1\\n/.test(t),
        sevenDayEmpty: t.includes('No activity yet'),
      });
    })()
    """

    JS_OPEN_SETTINGS = """
    (() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const settingsBtn = btns.find(b => b.textContent.trim() === 'Settings');
      if (settingsBtn) { settingsBtn.click(); return 'opened'; }
      return 'not found';
    })()
    """

    JS_MODAL_TEXT = """
    (() => {
      const modal = document.querySelector('[role="dialog"], [class*="modal"]');
      if (!modal) return JSON.stringify({text: ''});
      return JSON.stringify({text: modal.innerText.substring(0, 5000)});
    })()
    """

    @staticmethod
    def js_modal_click(tab_name: str) -> str:
        return f"""
        (() => {{
          const modal = document.querySelector('[role="dialog"], [class*="modal"]');
          if (!modal) return 'no modal';
          const allEls = Array.from(modal.querySelectorAll('*'));
          const el = allEls.find(e => e.textContent.trim() === '{tab_name}' && e.children.length === 0);
          if (el) {{ el.click(); return 'clicked'; }}
          const navEl = allEls.find(e => e.textContent.trim() === '{tab_name}' && e.className.includes('NavItem'));
          if (navEl) {{ navEl.click(); return 'clicked nav'; }}
          return 'not found';
        }})()
        """

    JS_FEED_SCROLL = """
    (async () => {
      let last = 0, stable = 0, i = 0;
      while (stable < 3 && i < 200) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 1000));
        const h = document.body.scrollHeight;
        if (h === last) stable++; else { stable = 0; last = h; }
        i++;
      }
      return JSON.stringify({iterations: i, finalHeight: last});
    })()
    """

    @staticmethod
    def js_extract_posts(slug: str) -> str:
        return f"""
        ((slug) => {{
          const anchors = [...document.querySelectorAll('a[href*="/' + slug + '/"]')]
            .filter(a => !a.href.includes('?p=') && !a.href.includes('/classroom') && !a.href.includes('/-/') && !a.href.includes('/about') && !a.href.includes('/calendar') && !a.href.includes('/map') && !a.href.endsWith('/' + slug) && !a.href.endsWith('/' + slug + '/'));
          const posts = [];
          const seen = new Set();
          for (const a of anchors) {{
            let el = a;
            for (let i = 0; i < 8 && el; i++) {{
              el = el.parentElement;
              if (el && el.innerText && el.innerText.length > 100) break;
            }}
            if (!el) continue;
            const txt = el.innerText;
            if (seen.has(txt)) continue;
            seen.add(txt);
            const lines = txt.split('\\n').map(s => s.trim()).filter(Boolean);
            const pinned = lines.includes('Pinned');
            const offset = pinned ? lines.indexOf('Pinned') + 1 : 0;
            const ncIdx = lines.findIndex(l => /^(New comment|Last comment)/.test(l));
            let likes = 0, comments = 0, lastCommentAge = null;
            if (ncIdx > 0) {{
              comments = parseInt(lines[ncIdx - 1]) || 0;
              likes = parseInt(lines[ncIdx - 2]) || 0;
              lastCommentAge = lines[ncIdx];
            }}
            let author = null, title = null, category = null;
            for (let i = offset; i < Math.min(offset + 8, lines.length); i++) {{
              if (/^\\d$/.test(lines[i]) || lines[i] === '🔥') continue;
              if (!author) {{ author = lines[i]; continue; }}
              if (/•/.test(lines[i])) continue;
              if (['🏠','❤️','🐺','General'].some(c => lines[i].startsWith(c))) {{ category = lines[i]; continue; }}
              title = lines[i];
              break;
            }}
            posts.push({{ href: a.href, pinned, author, category, title, likes, comments, lastCommentAge }});
          }}
          const byHref = {{}};
          for (const p of posts) if (!byHref[p.href]) byHref[p.href] = p;
          return JSON.stringify({{ count: Object.keys(byHref).length, posts: Object.values(byHref) }});
        }})('{slug}')
        """

    @staticmethod
    def js_check_admin_reply(admin_names: list) -> str:
        names_json = json.dumps(admin_names)
        return f"""
        ((adminNames) => {{
          const t = document.body.innerText;
          const found = adminNames.filter(name => {{
            const re = new RegExp(name.replace(/[\\s\\u00a0]/g, '[\\\\s\\\\u00a0]+'));
            return re.test(t);
          }});
          return JSON.stringify(found);
        }})({names_json})
        """

    # -- URL builders --

    @property
    def url_about(self): return f"{self.base}/about"
    @property
    def url_members(self): return f"{self.base}/-/members"
    @property
    def url_feed(self): return self.base
    @property
    def url_classroom(self): return f"{self.base}/classroom"
    @property
    def url_calendar(self): return f"{self.base}/calendar"
    @property
    def url_map(self): return f"{self.base}/-/map?is=1"
    @property
    def url_leaderboards(self): return f"{self.base}/-/leaderboards"
    @property
    def url_settings(self): return self.base  # settings is opened via button click

    async def run_section(self, page, section_name: str, js_snippet: str):
        """Run a JS snippet via page.evaluate; on failure return an error stub."""
        try:
            raw = await page.evaluate(js_snippet)
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except Exception:
                    return {"raw": raw}
            return raw
        except Exception as e:
            return {"error": str(e), "section": section_name}
