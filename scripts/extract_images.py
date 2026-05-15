#!/usr/bin/env python3
"""Extract base64 images from data/*.js files to images/ directory,
then rewrite the JS files to contain only question data."""

import os
import re
import base64

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
IMAGES_DIR = os.path.join(os.path.dirname(__file__), '..', 'images')

DATA_FILES = [
    'prirodniny.js',
    'rostliny.js',
    'souhvezdi.js',
    'dominanty.js',
    'topografie.js',
    'uzly.js',
]

# Matches: "key":"data:image/TYPE;base64,DATA" (with or without trailing comma)
IMAGE_LINE_RE = re.compile(r'^"([^"]+)":"data:image/([^;]+);base64,([A-Za-z0-9+/=]+)",?$')
# Matches: IMAGES_DATA["category"]={
IMAGES_BLOCK_START_RE = re.compile(r'^IMAGES_DATA\["([^"]+)"\]=\{$')

os.makedirs(IMAGES_DIR, exist_ok=True)

for filename in DATA_FILES:
    filepath = os.path.join(DATA_DIR, filename)
    print(f'Processing {filename}...')

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    kept_lines = []
    in_images_block = False
    current_cat = None
    images_extracted = 0

    for line in lines:
        stripped = line.rstrip('\n')

        # Skip the IMAGES_DATA global declaration
        if stripped == 'var IMAGES_DATA=window.IMAGES_DATA||(window.IMAGES_DATA={});':
            continue

        # Detect start of an IMAGES_DATA block
        m = IMAGES_BLOCK_START_RE.match(stripped)
        if m:
            current_cat = m.group(1)
            os.makedirs(os.path.join(IMAGES_DIR, current_cat), exist_ok=True)
            in_images_block = True
            continue

        if in_images_block:
            # Closing brace ends the block
            if stripped == '}':
                in_images_block = False
                current_cat = None
                continue

            # Image data line
            m = IMAGE_LINE_RE.match(stripped)
            if m:
                key, mime_type, b64_data = m.groups()
                ext = 'jpg' if mime_type == 'jpeg' else mime_type
                out_path = os.path.join(IMAGES_DIR, current_cat, f'{key}.{ext}')
                with open(out_path, 'wb') as f:
                    f.write(base64.b64decode(b64_data))
                images_extracted += 1
                continue

            # Unexpected line inside block — keep it and warn
            print(f'  WARNING: unexpected line in images block: {stripped[:80]}')
            kept_lines.append(line)
            continue

        kept_lines.append(line)

    # Write the stripped JS file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(kept_lines)

    print(f'  {images_extracted} images extracted, {filename} rewritten')

print('Done.')
