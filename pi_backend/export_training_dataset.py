import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE = Path(__file__).resolve().parent
ENV_FILE = BASE / ".env"
DEFAULT_OUTPUT = BASE / "training_export.json"


def load_simple_env(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_simple_env(ENV_FILE)

    token = os.getenv("ADMIN_EXPORT_TOKEN", "").strip()
    if not token:
        print("ADMIN_EXPORT_TOKEN is not configured in .env", file=sys.stderr)
        return 1

    base_url = os.getenv("EXPORT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    output_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_OUTPUT

    request = Request(
        f"{base_url}/admin/training-export",
        headers={"Authorization": f"Bearer {token}"},
    )

    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        print(f"Export failed with HTTP {exc.code}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported {payload.get('count', 0)} records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
