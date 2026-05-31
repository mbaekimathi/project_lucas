"""
Google Drive backups: OAuth user connection, school/year/term folder tree, categorized uploads.
"""

import json
import os
import re
from datetime import datetime

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    GOOGLE_DRIVE_LIBS = True
except ImportError:
    GOOGLE_DRIVE_LIBS = False

try:
    from google_auth_oauthlib.flow import Flow

    OAUTH_FLOW_AVAILABLE = True
except ImportError:
    OAUTH_FLOW_AVAILABLE = False

DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']
OAUTH_STATE_SESSION_KEY = 'google_drive_oauth_state'

# Term folder layout under each academic year / term
FOLDER_ACCOUNTS = 'Accounts backup'
FOLDER_CURRICULUM = 'Curriculum backup'
ACCOUNTS_SUBFOLDERS = ('fees', 'payments')
CURRICULUM_SUBFOLDERS = ('exams', 'timetable', 'attendance')


def oauth_client_configured():
    return bool((os.environ.get('GOOGLE_OAUTH_CLIENT_ID') or '').strip() and
                (os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET') or '').strip())


def _credentials_path():
    return (os.environ.get('GOOGLE_DRIVE_CREDENTIALS_FILE') or '').strip()


def _credentials_json_raw():
    return (os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON') or '').strip()


def service_account_configured():
    if not GOOGLE_DRIVE_LIBS:
        return False
    return bool(_credentials_path() and os.path.isfile(_credentials_path())) or bool(_credentials_json_raw())


def is_google_drive_configured():
    return oauth_client_configured() or service_account_configured()


def _oauth_redirect_uri():
    return (os.environ.get('GOOGLE_OAUTH_REDIRECT_URI') or '').strip() or 'http://127.0.0.1:5000/database/google-drive/callback'


def friendly_drive_error(exc):
    """Turn Google API errors into short user-facing messages."""
    text = str(exc)
    if 'accessNotConfigured' in text or 'has not been used in project' in text or 'it is disabled' in text:
        m = re.search(r'project (\d+)', text)
        pid = m.group(1) if m else ''
        link = (
            f'https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project={pid}'
            if pid
            else 'https://console.cloud.google.com/apis/library/drive.googleapis.com'
        )
        return (
            'Google Drive API is not enabled for your Google Cloud project. '
            f'Open this link, click Enable, wait 2–5 minutes, then try again: {link}'
        )
    if 'insufficient' in text.lower() or '403' in text:
        return f'Google Drive permission denied: {text[:200]}'
    return text[:400]


def configure_oauth_transport():
    """
    Allow http://127.0.0.1 OAuth callbacks in local dev (oauthlib requires HTTPS otherwise).
    Not used when GOOGLE_OAUTH_REDIRECT_URI is https (production).
    """
    uri = _oauth_redirect_uri()
    if uri.lower().startswith('http://'):
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def _load_service_account_credentials():
    raw = _credentials_json_raw()
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
    path = _credentials_path()
    if path and os.path.isfile(path):
        return service_account.Credentials.from_service_account_file(path, scopes=DRIVE_SCOPES)
    raise RuntimeError('Service account credentials not configured.')


def credentials_from_token_json(token_json):
    if not token_json:
        return None
    if isinstance(token_json, str):
        data = json.loads(token_json)
    else:
        data = token_json
    creds = Credentials(
        token=data.get('token'),
        refresh_token=data.get('refresh_token'),
        token_uri=data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=data.get('client_id') or os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
        client_secret=data.get('client_secret') or os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
        scopes=data.get('scopes') or DRIVE_SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def refresh_and_serialize_credentials(creds):
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return json.dumps({
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes) if creds.scopes else DRIVE_SCOPES,
    })


def get_service_account_email():
    try:
        raw = _credentials_json_raw()
        if raw:
            return json.loads(raw).get('client_email', '')
        path = _credentials_path()
        if path and os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f).get('client_email', '')
    except Exception:
        pass
    return ''


def is_user_connected(backup_settings):
    if not backup_settings:
        return False
    token = backup_settings.get('google_drive_oauth_token')
    return bool(token)


def get_drive_service(backup_settings=None):
    if not GOOGLE_DRIVE_LIBS:
        raise RuntimeError('Install google-api-python-client and google-auth.')
    if backup_settings and backup_settings.get('google_drive_oauth_token'):
        creds = credentials_from_token_json(backup_settings['google_drive_oauth_token'])
        if creds and creds.valid:
            return build('drive', 'v3', credentials=creds, cache_discovery=False), creds
    if service_account_configured():
        creds = _load_service_account_credentials()
        return build('drive', 'v3', credentials=creds, cache_discovery=False), creds
    raise RuntimeError('Connect Google Drive on the backup page first.')


def create_oauth_flow():
    configure_oauth_transport()
    if not OAUTH_FLOW_AVAILABLE:
        raise RuntimeError('Install google-auth-oauthlib for Google sign-in.')
    if not oauth_client_configured():
        raise RuntimeError('Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env.local or .env')
    client_config = {
        'web': {
            'client_id': os.environ['GOOGLE_OAUTH_CLIENT_ID'],
            'client_secret': os.environ['GOOGLE_OAUTH_CLIENT_SECRET'],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [_oauth_redirect_uri()],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=DRIVE_SCOPES)
    flow.redirect_uri = _oauth_redirect_uri()
    return flow


def _sanitize_folder_name(name):
    s = (name or 'Untitled').strip()
    s = re.sub(r'[\\/:*?"<>|]', '-', s)
    return s[:80] or 'Untitled'


def _escape_query_value(value):
    return (value or '').replace("'", "\\'")


def find_folder(service, name, parent_id):
    q = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{_escape_query_value(name)}' and trashed=false"
    )
    if parent_id:
        q += f" and '{parent_id}' in parents"
    else:
        q += " and 'root' in parents"
    res = service.files().list(q=q, fields='files(id, name)', pageSize=5).execute()
    files = res.get('files', [])
    return files[0]['id'] if files else None


def create_folder(service, name, parent_id):
    existing = find_folder(service, name, parent_id)
    if existing:
        return existing
    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        meta['parents'] = [parent_id]
    created = service.files().create(body=meta, fields='id').execute()
    return created['id']


def ensure_path(service, path_parts, parent_id):
    """path_parts: tuple of folder names; returns final folder id."""
    current = parent_id
    for part in path_parts:
        current = create_folder(service, _sanitize_folder_name(part), current)
    return current


def ensure_term_backup_folders(service, school_folder_id, year_name, term_name):
    """Create Accounts/Curriculum tree for one term. Returns dict of leaf folder ids."""
    year_id = create_folder(service, _sanitize_folder_name(year_name), school_folder_id)
    term_id = create_folder(service, _sanitize_folder_name(term_name), year_id)
    accounts_id = create_folder(service, FOLDER_ACCOUNTS, term_id)
    curriculum_id = create_folder(service, FOLDER_CURRICULUM, term_id)
    leaves = {}
    for sub in ACCOUNTS_SUBFOLDERS:
        leaves[('accounts', sub)] = create_folder(service, sub, accounts_id)
    for sub in CURRICULUM_SUBFOLDERS:
        leaves[('curriculum', sub)] = create_folder(service, sub, curriculum_id)
    return {
        'year_folder_id': year_id,
        'term_folder_id': term_id,
        'accounts_folder_id': accounts_id,
        'curriculum_folder_id': curriculum_id,
        'leaves': leaves,
    }


def build_folder_map(service, school_name, academic_calendar, root_parent_id=None):
    """
    academic_calendar: [{id, name, terms: [{id, name}]}]
    Returns folder_map JSON-serializable structure.
    """
    school_id = create_folder(service, _sanitize_folder_name(school_name), root_parent_id)
    school_map = {
        'school_folder_id': school_id,
        'school_name': school_name,
        'years': {},
        'updated_at': datetime.now().isoformat(),
    }
    for year in academic_calendar or []:
        yname = year.get('name') or f"Year {year.get('id')}"
        ykey = str(year.get('id') or yname)
        school_map['years'][ykey] = {'name': yname, 'terms': {}}
        for term in year.get('terms') or []:
            tname = term.get('name') or f"Term {term.get('id')}"
            tkey = str(term.get('id') or tname)
            tree = ensure_term_backup_folders(service, school_id, yname, tname)
            school_map['years'][ykey]['terms'][tkey] = {
                'name': tname,
                'term_folder_id': tree['term_folder_id'],
                'folders': {
                    f"accounts/{sub}": tree['leaves'][('accounts', sub)]
                    for sub in ACCOUNTS_SUBFOLDERS
                } | {
                    f"curriculum/{sub}": tree['leaves'][('curriculum', sub)]
                    for sub in CURRICULUM_SUBFOLDERS
                },
            }
    return school_map


def resolve_upload_folder_id(folder_map, year_id, term_id, drive_path):
    """drive_path e.g. 'accounts/fees' or 'curriculum/exams'"""
    if not folder_map:
        return None
    years = folder_map.get('years') or {}
    y = years.get(str(year_id)) or years.get(year_id)
    if not y:
        first = next(iter(years.values()), None)
        y = first
    if not y:
        return folder_map.get('school_folder_id')
    terms = y.get('terms') or {}
    t = terms.get(str(term_id)) or terms.get(term_id)
    if not t:
        t = next(iter(terms.values()), None)
    if not t:
        return folder_map.get('school_folder_id')
    return (t.get('folders') or {}).get(drive_path)


def upload_file_to_folder(service, local_path, folder_id, filename=None, description=''):
    if not os.path.isfile(local_path):
        return {'error': 'File not found'}
    name = filename or os.path.basename(local_path)
    media = MediaFileUpload(
        local_path,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        resumable=True,
    )
    meta = {'name': name, 'parents': [folder_id], 'description': description or ''}
    created = service.files().create(body=meta, media_body=media, fields='id, webViewLink').execute()
    return {
        'file_id': created.get('id'),
        'web_view_link': created.get('webViewLink'),
        'folder_id': folder_id,
    }


def upload_structured_backups(service, folder_map, year_id, term_id, file_paths, stamp=None):
    """
    file_paths: dict drive_path -> local filepath
    e.g. {'accounts/fees': '/path/fees.xlsx', ...}
    """
    stamp = stamp or datetime.now().strftime('%Y-%m-%d %H-%M')
    results = []
    errors = []
    for drive_path, local_path in file_paths.items():
        folder_id = resolve_upload_folder_id(folder_map, year_id, term_id, drive_path)
        if not folder_id:
            errors.append(f'No folder for {drive_path}')
            continue
        base = os.path.splitext(os.path.basename(local_path))[0]
        fname = f'{base}_{stamp}.xlsx'
        try:
            up = upload_file_to_folder(service, local_path, folder_id, fname)
            up['drive_path'] = drive_path
            results.append(up)
        except Exception as e:
            errors.append(f'{drive_path}: {e}')
    return {'uploads': results, 'errors': errors}


def test_connection(backup_settings=None, folder_id_override=None):
    if not is_google_drive_configured() and not is_user_connected(backup_settings or {}):
        return False, 'Connect Google Drive or configure credentials in .env.local or .env.'
    try:
        service, _ = get_drive_service(backup_settings)
        folder_id = (folder_id_override or
                     (backup_settings or {}).get('google_drive_folder_id') or
                     os.environ.get('GOOGLE_DRIVE_FOLDER_ID') or '').strip()
        if folder_id:
            f = service.files().get(fileId=folder_id, fields='id, name').execute()
            return True, f"Connected — folder: {f.get('name', folder_id)}"
        about = service.about().get(fields='user').execute()
        email = (about.get('user') or {}).get('emailAddress', '')
        return True, f'Connected as {email or "Google account"}'
    except Exception as e:
        return False, str(e)


def get_connected_user_email(backup_settings):
    if backup_settings and backup_settings.get('google_drive_connected_email'):
        return backup_settings['google_drive_connected_email']
    try:
        service, _ = get_drive_service(backup_settings)
        about = service.about().get(fields='user').execute()
        return (about.get('user') or {}).get('emailAddress', '')
    except Exception:
        return ''
