"""
Environment files (only these two):

  .env.local  — local development (your PC)
  .env        — production / cPanel hosting

If .env.local exists, it is loaded. Otherwise .env is loaded.
Neither file is committed to git.
"""
from pathlib import Path

_LOADED_FILE = None


def load_project_env(project_dir=None):
    """
    Load .env.local if present (local), else .env (hosted).
    Returns the path loaded, or None.
    """
    global _LOADED_FILE
    try:
        from dotenv import load_dotenv
    except ImportError:
        _LOADED_FILE = None
        return None

    base = Path(project_dir).resolve() if project_dir else Path(__file__).resolve().parent
    local_path = base / '.env.local'
    hosted_path = base / '.env'

    if local_path.is_file():
        load_dotenv(local_path)
        _LOADED_FILE = local_path
        return local_path
    if hosted_path.is_file():
        load_dotenv(hosted_path)
        _LOADED_FILE = hosted_path
        return hosted_path

    _LOADED_FILE = None
    return None


def loaded_env_file():
    """Path to the env file that was loaded, or None."""
    return _LOADED_FILE


def env_file_label():
    """Short label for messages: '.env.local' or '.env'."""
    if _LOADED_FILE is None:
        return '.env or .env.local'
    return _LOADED_FILE.name
