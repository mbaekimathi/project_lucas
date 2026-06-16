#!/usr/bin/env python3
"""
Re-compress existing images under static/uploads/ (one-off maintenance).

Usage:
    python optimize_uploaded_images.py
"""

import os

from image_optimizer import PRESETS, is_image_filename, optimize_file_on_disk, pillow_available

ROOT = os.path.dirname(os.path.abspath(__file__))

FOLDER_PRESETS = (
    ('static/uploads/profiles', 'profile'),
    ('static/uploads/student_photos', 'student_photo'),
    ('static/uploads/store_inventory', 'store'),
    ('static/uploads/payment_proofs', 'payment_proof'),
    ('static/uploads/communication', 'attachment'),
)


def _preset_for_file(folder_preset, filename):
    lower = filename.lower()
    if folder_preset == 'profile':
        if lower.startswith('school_hero_'):
            return 'hero'
        if lower.startswith('school_logo_'):
            return 'logo'
    return folder_preset


def main():
    if not pillow_available():
        print('Pillow is not installed. Run: pip install Pillow')
        return 1

    total_saved = 0
    total_files = 0

    for rel_folder, default_preset in FOLDER_PRESETS:
        folder = os.path.join(ROOT, rel_folder)
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not os.path.isfile(path) or not is_image_filename(name):
                continue
            preset = _preset_for_file(default_preset, name)
            saved = optimize_file_on_disk(path, preset=preset, inplace=True)
            total_saved += saved
            total_files += 1
            if saved > 0:
                print(f'  saved {saved // 1024} KB  {rel_folder}/{name}')

    print(f'Done. Optimized {total_files} file(s); freed ~{total_saved // 1024} KB.')
    print('Preset summary:', ', '.join(sorted(PRESETS)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
