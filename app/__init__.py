from __future__ import annotations

from pathlib import Path

# Compatibility shim:
# allow imports like `from app...` to resolve when the project is started
# from the repository root via `uvicorn backend.app.main:app --reload`.
_BACKEND_APP_DIR = Path(__file__).resolve().parents[1] / 'backend' / 'app'

if _BACKEND_APP_DIR.exists():
    __path__ = [str(_BACKEND_APP_DIR)]
else:
    __path__ = []
