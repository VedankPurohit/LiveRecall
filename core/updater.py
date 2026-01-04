"""
LiveRecall Auto-Update Checker
Checks GitHub releases for new versions
"""

import threading
from collections.abc import Callable

import httpx

# Current version
VERSION = "0.1.2"
GITHUB_REPO = "VedankPurohit/LiveRecall"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse version string like '0.1.0' into tuple (0, 1, 0)"""
    # Strip 'v' prefix if present
    version_str = version_str.lstrip("v")
    try:
        return tuple(int(x) for x in version_str.split("."))
    except ValueError:
        return (0, 0, 0)


def is_newer_version(latest: str, current: str = VERSION) -> bool:
    """Check if latest version is newer than current"""
    return parse_version(latest) > parse_version(current)


def check_for_updates() -> dict | None:
    """
    Check GitHub for new releases.

    Returns dict with update info if available, None otherwise.
    Returns None on any error (network, API, etc.)
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                RELEASES_URL,
                headers={"Accept": "application/vnd.github.v3+json"},
                follow_redirects=True,
            )

            if response.status_code != 200:
                return None

            data = response.json()
            latest_version = data.get("tag_name", "").lstrip("v")

            if not latest_version:
                return None

            if is_newer_version(latest_version, VERSION):
                return {
                    "current_version": VERSION,
                    "latest_version": latest_version,
                    "release_url": data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases"),
                    "release_name": data.get("name", f"v{latest_version}"),
                    "release_notes": data.get("body", ""),
                    "published_at": data.get("published_at", ""),
                }

            return None

    except Exception:
        # Silently fail - update check is not critical
        return None


def check_for_updates_async(callback: Callable[[dict | None], None]):
    """
    Check for updates in background thread.
    Calls callback with result (update info dict or None).
    """

    def _check():
        result = check_for_updates()
        callback(result)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()


if __name__ == "__main__":
    print(f"Current version: {VERSION}")
    print("Checking for updates...")

    update = check_for_updates()
    if update:
        print(f"Update available: {update['latest_version']}")
        print(f"Download: {update['release_url']}")
    else:
        print("You're on the latest version!")
