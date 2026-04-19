"""Credential retrieval via 1Password CLI."""
import subprocess
import json


def get_credentials(item_name: str) -> dict:
    """Fetch username + password from 1Password by item name."""
    try:
        out = subprocess.check_output(
            ["op", "item", "get", item_name, "--format", "json"],
            stderr=subprocess.DEVNULL,
        ).decode()
        data = json.loads(out)
        result = {}
        for field in data.get("fields", []):
            label = field.get("label", "").lower()
            if label in ("username", "email"):
                result["username"] = field.get("value", "")
            elif label == "password":
                result["password"] = field.get("value", "")
        return result
    except Exception as e:
        raise RuntimeError(f"1Password lookup failed for '{item_name}': {e}")


def get_skool_credentials() -> dict:
    return get_credentials("Skool")
