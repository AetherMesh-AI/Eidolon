"""Derive uncropped desktop icons using the repository's declared Pillow dependency.

Run: python3 apps/desktop/scripts/derive-app-icons.py
The immutable supplied PNG is retained; no agent-avatar assets are touched.
"""
from pathlib import Path
import hashlib
import json
import shutil

from PIL import Image, __version__

DESKTOP = Path(__file__).resolve().parents[1]
ASSETS = DESKTOP / 'assets'
SOURCE = ASSETS / 'app-icon-source.png'


def main():
    source = SOURCE.read_bytes()
    image = Image.open(SOURCE).convert('RGBA')
    # Refuse other geometry rather than crop/stretch the supplied square artwork.
    assert image.size == (1254, 1254)
    image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
    image.save(ASSETS / 'icon.png')
    image.save(ASSETS / 'icon.icns', format='ICNS')
    sizes = [16, 24, 32, 48, 64, 128, 256]
    image.save(ASSETS / 'icon.ico', format='ICO', sizes=[(n, n) for n in sizes])
    shutil.copyfile(ASSETS / 'icon.png', DESKTOP / 'public/icon.png')
    (ASSETS / 'app-icon-provenance.json').write_text(json.dumps({

        'source_sha256': hashlib.sha256(source).hexdigest(),
        'source_dimensions': [1254, 1254],
        'transform': 'Pillow LANCZOS proportional resize; entire square source, no crop or redesign',
        'generator': 'apps/desktop/scripts/derive-app-icons.py',
        'pillow_version': __version__,
        'icns': 'PNG-backed ICNS with 128 through 1024 pixel representations',
        'ico': sizes,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
