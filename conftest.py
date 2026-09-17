"""Root pytest conftest. The backend package (`app.*`) lives under backend/, while
`models.*`/`data.*`/`simulation.*`/`financial.*` live at the repo root — both need to be
importable the same way the running server sees them (see scripts/run_backend.sh)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
for p in (ROOT, ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
