"""Update data.json from an authorized JSON sales provider.

The initial zero values are placeholders, not verified Weidian counts. This
script deliberately does not scrape Weidian pages or guess private endpoints.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"
MAX_RESPONSE_BYTES = 1_000_000


def log(message: str) -> None:
    print(message, file=sys.stderr)


def fetch_provider(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("SALES_PROVIDER_URL must be an HTTPS URL")
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "YulequanRanking/1.0"})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f"Provider returned HTTP {response.status}")
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("Provider response is too large")
    payload = json.loads(body)
    if not isinstance(payload, dict) or not isinstance(payload.get("sales"), dict):
        raise ValueError("Provider response must be an object with a sales object")
    return payload["sales"]


def atomic_write(data: dict) -> None:
    fd, temp_name = tempfile.mkstemp(prefix="data.", suffix=".tmp", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, DATA_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    provider_url = os.environ.get("SALES_PROVIDER_URL", "").strip()
    if not provider_url:
        log("No authorized provider configured; keeping all existing values unchanged.")
        return 0

    try:
        current = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        sales = fetch_provider(provider_url)
        if not isinstance(current.get("characters"), list) or not current["characters"]:
            raise ValueError("data.json has no configured characters")
        changed = 0
        for character in current["characters"]:
            value = sales.get(character["id"])
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                log(f"No valid sales value for {character.get('id', 'unknown')}; keeping its last value.")
                continue
            character["sales"] = value
            character["salesVerified"] = True
            changed += 1
        if changed == 0:
            raise ValueError("Provider response contained no valid sales values; data was not changed")
        current["lastUpdated"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        current["sourceStatus"] = "partial" if changed < len(current["characters"]) else "verified"
        atomic_write(current)
        print(f"Updated {changed}/{len(current['characters'])} characters at {current['lastUpdated']}.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, URLError) as error:
        # Error text is intentionally not echoed: URL errors may contain secret query strings.
        log(f"Sales update failed ({type(error).__name__}); previous data retained.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
