"""Reusable pagination helpers for Playwright-driven Skool scans."""
import asyncio


async def scroll_until_stable(page, stable_iterations: int = 3, max_iterations: int = 200, wait_ms: int = 1000) -> dict:
    last_height = 0
    stable = 0
    i = 0
    while stable < stable_iterations and i < max_iterations:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(wait_ms / 1000)
        height = await page.evaluate("document.body.scrollHeight")
        if height == last_height:
            stable += 1
        else:
            stable = 0
            last_height = height
        i += 1
    return {"iterations": i, "final_height": last_height, "stabilized": stable >= stable_iterations}


async def scroll_until_date_cutoff(page, extract_dates_js: str, cutoff_days: int = 90, max_iterations: int = 300, wait_ms: int = 1000) -> dict:
    """Scroll until posts older than cutoff appear. extract_dates_js returns list of age strings."""
    i = 0
    hit_cutoff = False
    while i < max_iterations and not hit_cutoff:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(wait_ms / 1000)
        ages = await page.evaluate(extract_dates_js)
        if isinstance(ages, list):
            for a in ages:
                if _age_exceeds(a, cutoff_days):
                    hit_cutoff = True
                    break
        i += 1
    return {"iterations": i, "hit_cutoff": hit_cutoff}


def _age_exceeds(age_str: str, cutoff_days: int) -> bool:
    if not age_str or not isinstance(age_str, str):
        return False
    s = age_str.lower()
    if "year" in s:
        return True
    if "month" in s:
        try:
            n = int("".join(c for c in s if c.isdigit()) or "0")
            return n * 30 >= cutoff_days
        except Exception:
            return True
    if "day" in s:
        try:
            n = int("".join(c for c in s if c.isdigit()) or "0")
            return n >= cutoff_days
        except Exception:
            return False
    return False
