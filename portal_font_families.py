"""Portal typography options — Google Fonts + system stack (system settings / site-wide theme)."""

PORTAL_FONT_FAMILIES = [
  # Sans-serif — UI & corporate
  {'value': 'Inter', 'group': 'Sans-serif — UI & corporate', 'hint': 'Modern dashboards and admin UIs', 'google': 'Inter'},
  {'value': 'Roboto', 'group': 'Sans-serif — UI & corporate', 'hint': 'Material Design · widely adopted', 'google': 'Roboto'},
  {'value': 'Open Sans', 'group': 'Sans-serif — UI & corporate', 'hint': 'Neutral, readable corporate body text', 'google': 'Open Sans'},
  {'value': 'Poppins', 'group': 'Sans-serif — UI & corporate', 'hint': 'Geometric · marketing-friendly', 'google': 'Poppins'},
  {'value': 'Lato', 'group': 'Sans-serif — UI & corporate', 'hint': 'Humanist · approachable institutions', 'google': 'Lato'},
  {'value': 'Source Sans 3', 'group': 'Sans-serif — UI & corporate', 'hint': 'Adobe · documentation & ERP-style UIs', 'google': 'Source Sans 3'},
  {'value': 'Nunito Sans', 'group': 'Sans-serif — UI & corporate', 'hint': 'Soft rounded · schools & family portals', 'google': 'Nunito Sans'},
  {'value': 'Work Sans', 'group': 'Sans-serif — UI & corporate', 'hint': 'Clean · data-heavy tables', 'google': 'Work Sans'},
  {'value': 'DM Sans', 'group': 'Sans-serif — UI & corporate', 'hint': 'Product UI · contemporary SaaS', 'google': 'DM Sans'},
  {'value': 'IBM Plex Sans', 'group': 'Sans-serif — UI & corporate', 'hint': 'Enterprise · technical products', 'google': 'IBM Plex Sans'},
  {'value': 'Manrope', 'group': 'Sans-serif — UI & corporate', 'hint': 'Modern geometric · fintech & SaaS', 'google': 'Manrope'},
  {'value': 'Plus Jakarta Sans', 'group': 'Sans-serif — UI & corporate', 'hint': 'Startup / ed-tech product chrome', 'google': 'Plus Jakarta Sans'},
  {'value': 'Montserrat', 'group': 'Sans-serif — UI & corporate', 'hint': 'Strong headings · brand-forward sites', 'google': 'Montserrat'},
  {'value': 'Raleway', 'group': 'Sans-serif — UI & corporate', 'hint': 'Elegant · light corporate marketing', 'google': 'Raleway'},
  {'value': 'Ubuntu', 'group': 'Sans-serif — UI & corporate', 'hint': 'Friendly · open, community-facing', 'google': 'Ubuntu'},
  # Creative — professional (distinctive but credible)
  {'value': 'Outfit', 'group': 'Creative — professional', 'hint': 'Warm geometric · modern schools & ed-tech', 'google': 'Outfit', 'badge': 'Recommended'},
  {'value': 'Figtree', 'group': 'Creative — professional', 'hint': 'Friendly character · approachable brand', 'google': 'Figtree', 'badge': 'Recommended'},
  {'value': 'Sora', 'group': 'Creative — professional', 'hint': 'Tech-forward · innovation & STEM programs', 'google': 'Sora'},
  {'value': 'Space Grotesk', 'group': 'Creative — professional', 'hint': 'Editorial tech · memorable headings', 'google': 'Space Grotesk'},
  {'value': 'Lexend', 'group': 'Creative — professional', 'hint': 'Designed for readability · inclusive learning', 'google': 'Lexend'},
  {'value': 'Bricolage Grotesque', 'group': 'Creative — professional', 'hint': 'Expressive grotesk · standout portals', 'google': 'Bricolage Grotesque'},
  {'value': 'Fraunces', 'group': 'Creative — professional', 'hint': 'Distinctive serif · heritage & arts programs', 'google': 'Fraunces'},
  # Serif — formal & reports
  {'value': 'Source Serif 4', 'group': 'Serif — formal & reports', 'hint': 'Professional reports & letters', 'google': 'Source Serif 4'},
  {'value': 'Merriweather', 'group': 'Serif — formal & reports', 'hint': 'Readable long-form · policies', 'google': 'Merriweather'},
  {'value': 'Lora', 'group': 'Serif — formal & reports', 'hint': 'Editorial · certificates', 'google': 'Lora'},
  {'value': 'Libre Baskerville', 'group': 'Serif — formal & reports', 'hint': 'Traditional formal documents', 'google': 'Libre Baskerville'},
  # System
  {'value': 'System UI', 'group': 'System', 'hint': 'Segoe UI, San Francisco, Roboto — no web font load', 'google': None},
]

_PORTAL_FONT_VALUE_SET = frozenset(f['value'] for f in PORTAL_FONT_FAMILIES)

PORTAL_FONT_GROUP_ORDER = (
  'Creative — professional',
  'Sans-serif — UI & corporate',
  'Serif — formal & reports',
  'System',
)


def portal_fonts_grouped():
  """Fonts in display order for the theme picker UI."""
  buckets = {g: [] for g in PORTAL_FONT_GROUP_ORDER}
  for entry in PORTAL_FONT_FAMILIES:
    group = entry['group']
    if group not in buckets:
      buckets[group] = []
    buckets.setdefault(group, []).append(entry)
  ordered = []
  seen = set(PORTAL_FONT_GROUP_ORDER)
  for group in PORTAL_FONT_GROUP_ORDER:
    if buckets.get(group):
      ordered.append((group, buckets[group]))
  for group, items in buckets.items():
    if group not in seen and items:
      ordered.append((group, items))
  return ordered

SYSTEM_UI_FONT_STACK = (
  "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
  "'Helvetica Neue', Arial, sans-serif"
)


def font_family_values():
  return tuple(_PORTAL_FONT_VALUE_SET)


def normalize_portal_font_family(name):
  """Return a valid portal font value; default Inter."""
  value = (name or 'Inter').strip()
  return value if value in _PORTAL_FONT_VALUE_SET else 'Inter'


def portal_font_css_stack(font_name):
  """CSS font-family stack for :root / body."""
  name = normalize_portal_font_family(font_name)
  if name == 'System UI':
    return SYSTEM_UI_FONT_STACK
  safe = name.replace("'", "\\'")
  return f"'{safe}', system-ui, sans-serif"


def portal_tailwind_font_family(font_name):
  """Font family list for Tailwind fontFamily.sans / heading."""
  name = normalize_portal_font_family(font_name)
  if name == 'System UI':
    return [
      'system-ui',
      '-apple-system',
      'BlinkMacSystemFont',
      'Segoe UI',
      'Roboto',
      'Helvetica Neue',
      'Arial',
      'sans-serif',
    ]
  return [name, 'system-ui', 'sans-serif']


def portal_google_fonts_stylesheet_href(font_names=None):
  """
  Build Google Fonts CSS2 URL.
  font_names: iterable of display names, or None to load every web font (theme picker preview).
  """
  if font_names is None:
    entries = [f for f in PORTAL_FONT_FAMILIES if f.get('google')]
  else:
    wanted = frozenset(normalize_portal_font_family(n) for n in font_names)
    wanted = {n for n in wanted if n != 'System UI'}
    entries = [f for f in PORTAL_FONT_FAMILIES if f['value'] in wanted and f.get('google')]
  if not entries:
    return None
  param = '&'.join(
    f"family={f['google'].replace(' ', '+')}:wght@400;500;600;700" for f in entries
  )
  return f'https://fonts.googleapis.com/css2?{param}&display=swap'
