import asyncio
import random

try:
    from humancursor import WebCursor
    HAS_HUMANCURSOR = True
except ImportError:
    HAS_HUMANCURSOR = False


async def human_delay(min_s: float = 1.2, max_s: float = 3.5):
    """Log-normal distributed delay matching real human timing."""
    mu = (min_s + max_s) / 2
    sigma = (max_s - min_s) / 6
    delay = max(min_s, min(max_s, random.gauss(mu, sigma)))
    await asyncio.sleep(delay)


async def human_click(page, selector: str):
    """Move mouse to element with bezier curve, then click."""
    el = await page.query_selector(selector)
    if not el:
        raise ValueError(f"Element not found: {selector}")

    if HAS_HUMANCURSOR:
        cursor = WebCursor(page)
        await cursor.move_to(el)
        await asyncio.sleep(random.uniform(0.08, 0.2))
    else:
        box = await el.bounding_box()
        if box:
            x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
            y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.08, 0.2))

    await el.click()


async def human_type(page, selector: str, text: str):
    """Click field then type with realistic per-character delays."""
    await human_click(page, selector)
    await asyncio.sleep(random.uniform(0.3, 0.7))
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.07, 0.18))
