"""
Load environment: .env (hosted/defaults) then .env.local (overrides) for local dev.
On the server, use only .env. On your PC, use .env.local — do not copy production .env to dev.
"""
from pathlib import Path


def load_project_env(project_dir=None):
    """Load .env, then if present .env.local (override) so local and hosted differ."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    base = Path(project_dir).resolve() if project_dir else Path(__file__).resolve().parent
    p = base / ".env"
    if p.is_file():
        load_dotenv(p)
    local = base / ".env.local"
    if local.is_file():
        load_dotenv(local, override=True)
