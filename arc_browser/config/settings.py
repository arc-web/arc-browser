import os
import subprocess
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
EXTENSIONS_DIR = os.path.join(BASE_DIR, "extensions")


def detect_monitor2_x() -> int:
    """Get primary display width to use as X offset for second monitor."""
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            stderr=subprocess.DEVNULL,
        ).decode()
        data = json.loads(out)
        displays = data.get("SPDisplaysDataType", [{}])[0].get("spdisplays_ndrvs", [])
        if displays:
            res = displays[0].get("_spdisplays_resolution", "1920 x 1080")
            width = int(res.split("x")[0].strip().split(" ")[0])
            return width
    except Exception:
        pass
    return 1920


SECOND_MONITOR_X = detect_monitor2_x()
VPS_BROWSERLESS_URL = os.getenv("VPS_BROWSERLESS_URL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
