"""
Environment files (only these two):

  .env.local  — local development (your PC)
  .env        — production / cPanel hosting

Local PC: prefers .env.local when present.
cPanel/hosted path: always prefers .env (ignores a mistakenly uploaded .env.local).
Neither file is committed to git.
"""
from pathlib import Path

_LOADED_FILE = None
_IGNORED_LOCAL_ON_HOST = False


def _path_looks_hosted(base: Path) -> bool:
    """True for typical cPanel / shared-host app roots (never Windows drive paths)."""
    p = str(base.resolve()).replace('\\', '/')
    # Windows local paths are never "hosted"
    if len(p) >= 2 and p[1] == ':':
        return False
    markers = (
        '/home1/',
        '/home2/',
        '/home/',
        '/public_html',
        '/elimu_centric',
        '/project_lucas',
        '/kwetude',
        '/kanyakine',
        '/SCHOOL',
    )
    return any(m in p for m in markers)


def load_project_env(project_dir=None):
    """
    Load the correct env file for this machine.
    Returns the path loaded, or None.
    """
    global _LOADED_FILE, _IGNORED_LOCAL_ON_HOST
    _IGNORED_LOCAL_ON_HOST = False
    try:
        from dotenv import load_dotenv
    except ImportError:
        _LOADED_FILE = None
        return None

    base = Path(project_dir).resolve() if project_dir else Path(__file__).resolve().parent
    local_path = base / '.env.local'
    hosted_path = base / '.env'

    # On the live server, never let an accidental .env.local override production .env
    if _path_looks_hosted(base) and hosted_path.is_file():
        if local_path.is_file():
            _IGNORED_LOCAL_ON_HOST = True
            try:
                print(
                    "WARNING: .env.local found on hosted server - ignoring it and loading .env. "
                    "Delete .env.local from the server so production always uses .env."
                )
            except Exception:
                pass
        load_dotenv(hosted_path, override=True)
        _LOADED_FILE = hosted_path
        return hosted_path

    # Local development
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


def ignored_local_env_on_host():
    """True when .env.local was present but skipped because we are on hosted."""
    return _IGNORED_LOCAL_ON_HOST
