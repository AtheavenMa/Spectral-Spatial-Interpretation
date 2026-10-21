"""Keep the Python API's packaged frontend renderer identical to the browser one."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "playground" / "atlas-render.js"
DEPLOYED = ROOT / "lab" / "static" / "atlas-render.js"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if copies differ")
    args = parser.parse_args()
    canonical = SOURCE.read_bytes()
    if args.check:
        if not DEPLOYED.is_file() or DEPLOYED.read_bytes() != canonical:
            print("Renderer differs. Run: python tools/sync_atlas_renderer.py")
            return 1
        print("Shared Atlas renderer is synchronized.")
        return 0
    DEPLOYED.write_bytes(canonical)
    print(f"Updated {DEPLOYED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
