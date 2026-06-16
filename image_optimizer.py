"""
Resize, strip metadata, and compress uploaded images for lighter storage and faster pages.
"""

from __future__ import annotations

import io
import os

try:
    from PIL import Image, ImageOps

    _PILLOW_AVAILABLE = True
except ImportError:
    _PILLOW_AVAILABLE = False

IMAGE_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'gif', 'webp'})

# max_px: longest edge; max_h: optional height cap (hero banners)
PRESETS = {
    'profile': {'max_px': 400, 'quality': 82},
    'student_photo': {'max_px': 480, 'quality': 82},
    'store': {'max_px': 800, 'quality': 84},
    'hero': {'max_px': 1920, 'max_h': 1080, 'quality': 85},
    'logo': {'max_px': 480, 'quality': 88, 'keep_png_alpha': True},
    'payment_proof': {'max_px': 1400, 'quality': 82},
    'attachment': {'max_px': 1200, 'quality': 82},
}


def pillow_available():
    return _PILLOW_AVAILABLE


def is_image_filename(filename):
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS


def _preset(name):
    return PRESETS.get(name) or PRESETS['profile']


def _has_transparency(img):
    if img.mode in ('RGBA', 'LA'):
        return True
    if img.mode == 'P':
        try:
            return 'transparency' in img.info
        except Exception:
            return False
    return False


def _fit_image(img, max_px, max_h=None):
    w, h = img.size
    if max_h and h > max_h:
        scale = max_h / float(h)
        w = max(1, int(w * scale))
        h = max_h
        img = img.resize((w, h), Image.Resampling.LANCZOS)

    longest = max(img.size)
    if longest > max_px:
        scale = max_px / float(longest)
        nw = max(1, int(img.size[0] * scale))
        nh = max(1, int(img.size[1] * scale))
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img


def _image_from_bytes(data):
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    return img


def _read_storage(file_storage):
    stream = getattr(file_storage, 'stream', None) or file_storage
    if hasattr(stream, 'seek'):
        stream.seek(0)
    data = stream.read()
    if hasattr(stream, 'seek'):
        stream.seek(0)
    return data


def _save_jpeg(img, path, quality):
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    img.save(path, format='JPEG', quality=quality, optimize=True, progressive=True)


def _save_png(img, path):
    if img.mode not in ('RGBA', 'RGB', 'P', 'L'):
        img = img.convert('RGBA')
    img.save(path, format='PNG', optimize=True)


def optimize_image_bytes(data, preset='profile'):
    """
    Optimize in-memory image bytes. Returns (bytes, ext) e.g. (b'...', 'jpg')
    or (original_data, original_ext) when Pillow is unavailable.
    """
    if not data:
        return None, None
    if not _PILLOW_AVAILABLE:
        return data, None

    cfg = _preset(preset)
    try:
        img = _image_from_bytes(data)
    except Exception:
        return data, None

    img = _fit_image(img, cfg['max_px'], cfg.get('max_h'))
    quality = int(cfg.get('quality', 82))
    keep_alpha = cfg.get('keep_png_alpha') and _has_transparency(img)

    out = io.BytesIO()
    if keep_alpha:
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        img.save(out, format='PNG', optimize=True)
        return out.getvalue(), 'png'

    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    img.save(out, format='JPEG', quality=quality, optimize=True, progressive=True)
    return out.getvalue(), 'jpg'


def optimize_and_save(file_storage, dest_path, preset='profile'):
    """
    Optimize a uploaded image and write to disk.
    dest_path may include any extension; final file uses .jpg or .png as appropriate.
    Returns absolute path written, or None on failure / non-image.
    """
    if not file_storage:
        return None

    filename = (getattr(file_storage, 'filename', None) or '').strip()
    if filename and not is_image_filename(filename):
        return None

    directory = os.path.dirname(dest_path)
    stem = os.path.splitext(os.path.basename(dest_path))[0]
    os.makedirs(directory, exist_ok=True)

    data = _read_storage(file_storage)
    if not data:
        return None

    if not _PILLOW_AVAILABLE:
        fallback = dest_path if '.' in os.path.basename(dest_path) else f'{dest_path}.jpg'
        with open(fallback, 'wb') as fh:
            fh.write(data)
        return fallback

    try:
        optimized, ext = optimize_image_bytes(data, preset=preset)
    except Exception as exc:
        print(f'optimize_and_save: {exc}')
        fallback = dest_path if '.' in os.path.basename(dest_path) else f'{dest_path}.jpg'
        with open(fallback, 'wb') as fh:
            fh.write(data)
        return fallback

    if not optimized:
        return None

    if not ext:
        ext = 'jpg'
    final_path = os.path.join(directory, f'{stem}.{ext}')

    # Remove alternate extension if replacing an earlier save attempt
    for alt in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        alt_path = os.path.join(directory, f'{stem}.{alt}')
        if alt_path != final_path and os.path.isfile(alt_path):
            try:
                os.remove(alt_path)
            except OSError:
                pass

    with open(final_path, 'wb') as fh:
        fh.write(optimized)
    return final_path


def optimize_file_on_disk(path, preset='profile', inplace=True):
    """
    Re-compress an existing image file. Returns bytes saved (positive = smaller) or 0.
    Skips non-images and PDFs.
    """
    if not path or not os.path.isfile(path):
        return 0
    ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
    if ext not in IMAGE_EXTENSIONS:
        return 0
    if not _PILLOW_AVAILABLE:
        return 0

    try:
        before = os.path.getsize(path)
        with open(path, 'rb') as fh:
            data = fh.read()
        optimized, new_ext = optimize_image_bytes(data, preset=preset)
        if not optimized or not new_ext:
            return 0

        directory = os.path.dirname(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        final_path = os.path.join(directory, f'{stem}.{new_ext}')

        with open(final_path, 'wb') as fh:
            fh.write(optimized)

        if inplace and final_path != path and os.path.isfile(path):
            os.remove(path)

        after = os.path.getsize(final_path)
        return max(0, before - after)
    except Exception as exc:
        print(f'optimize_file_on_disk({path}): {exc}')
        return 0


def static_relative_path(absolute_path):
    """Map filesystem path under static/ to uploads/... URL fragment."""
    if not absolute_path:
        return None
    norm = absolute_path.replace('\\', '/')
    if '/static/' in norm:
        return norm.split('/static/', 1)[1]
    if norm.startswith('static/'):
        return norm[7:]
    return norm
