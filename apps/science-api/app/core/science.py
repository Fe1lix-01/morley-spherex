"""Locate the repository science package when uvicorn is started inside science-api."""
import sys
from app.core.paths import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from science.pipeline.region import Region  # noqa: E402,F401
