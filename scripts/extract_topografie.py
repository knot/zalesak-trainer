#!/usr/bin/env python3
"""Re-extract map symbols from Mapové značky 2019.pdf.
Grid layout: 2 pages × 2 grids × (3 cols × 4 rows) = 48 symbols total.
"""

import fitz, io, json, os, random, re
from PIL import Image

ROOT     = os.path.join(os.path.dirname(__file__), '..')
PDF_PATH = os.path.join(ROOT, 'uploads', 'Mapové značky 2019.pdf')
IMG_DIR  = os.path.join(ROOT, 'images', 'topografie')
JSON_OUT = os.path.join(ROOT, 'data', 'questions', 'topografie.json')

random.seed(42)

# ── Labels in PDF order (left→right, top→bottom) ───────────────────────────
ALL_LABELS = [
    # Page 0, Grid 1 (symbols 1–12)
    'Zpevněná cesta', 'Pěšina', 'Polní a lesní cesta',
    'Trasa vodní dopravy', 'Ostatní silnice', 'Silnice I. třídy',
    'Dálnice', 'Násep', 'Řeka s jezem',
    'Řeka s mostem', 'Řeka s přehradou', 'Řeka s přívozem',
    # Page 0, Grid 2 (symbols 13–24)
    'Kostel', 'Meteorologická stanice', 'Kaple',
    'Pomník', 'Zřícenina hradu', 'Veřejné tábořiště',
    'Autokempink', 'Hrad, zámek, tvrz', 'Kříž',
    'Větrný mlýn', 'Vodní mlýn', 'Orientačně důležitý strom',
    # Page 1, Grid 1 (symbols 25–36)
    'Muzeum, galerie', 'Hraniční přechod', 'Hraniční přechod pro pěší a cyklisty',
    'Kulturně pozoruhodné místo', 'Ubytovna', 'Hotel',
    'Stanice horské služby', 'Restaurace', 'Hranice CHKO',
    'Hranice národního parku', 'Hranice přírodního parku', 'Přírodní zajímavost',
    # Page 1, Grid 2 (symbols 37–48)
    'Sad a zahrada', 'Vinice', 'Porosty křoví',
    'Chmelnice', 'Vodojem', 'Pramen',
    'Veřejné koupaliště', 'Studna', 'Elektrárna',
    'Hájovna, myslivna', 'Továrna s komínem', 'Samostatná budova',
]

# ── Grid coordinates at 3× render scale ────────────────────────────────────
SCALE = 3.0
XS    = [126, 326, 526, 726]   # column splits (same for all grids)

# (page_index, [row_splits])  — 4 row splits define 3 inter-row gaps = 12 cells
GRIDS = [
    (0, [475,  588,  693,  940, 1120]),   # page 0, grid 1: thin-line road symbols
    (0, [1140, 1345, 1550, 1765, 2020]),  # page 0, grid 2: icons
    (1, [270,  446,  623,  801,  975]),   # page 1, grid 1: boundary/building icons
    (1, [1030, 1228, 1430, 1621, 1812]),  # page 1, grid 2: land-use/utility icons
]

def to_key(name):
    name = name.lower().strip()
    for a, b in [('á','a'),('č','c'),('ď','d'),('é','e'),('ě','e'),('í','i'),
                 ('ň','n'),('ó','o'),('ř','r'),('š','s'),('ť','t'),('ú','u'),
                 ('ů','u'),('ý','y'),('ž','z')]:
        name = name.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '_', name).strip('_')

def save_jpeg(pil_img, path, max_px=300, quality=88):
    img = pil_img.convert('RGB')
    w, h = img.size
    if max(w, h) > max_px:
        r = max_px / max(w, h)
        img = img.resize((int(w*r), int(h*r)), Image.LANCZOS)
    img.save(path, 'JPEG', quality=quality, optimize=True)

def make_options(correct, pool, n=4):
    others = [x for x in pool if x != correct]
    random.shuffle(others)
    opts = [correct] + others[:n-1]
    random.shuffle(opts)
    return opts

# ── Main extraction ─────────────────────────────────────────────────────────
os.makedirs(IMG_DIR, exist_ok=True)
doc = fitz.open(PDF_PATH)

# Cache rendered pages
pages = {}
for page_idx in set(g[0] for g in GRIDS):
    page = doc[page_idx]
    pix  = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
    pages[page_idx] = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)

doc.close()

label_idx = 0
questions  = []

for page_idx, row_splits in GRIDS:
    img = pages[page_idx]
    for row in range(4):
        y0, y1 = row_splits[row], row_splits[row + 1]
        for col in range(3):
            x0, x1 = XS[col], XS[col + 1]
            label = ALL_LABELS[label_idx]
            key   = to_key(label)

            cell = img.crop((x0, y0, x1, y1))
            out  = os.path.join(IMG_DIR, f'{key}.jpg')
            save_jpeg(cell, out)

            questions.append({
                'q':        'Co označuje tato mapová značka?',
                'img':      f'topografie/{key}',
                'imgClass': 'topo',
                'a':        label,
                'options':  make_options(label, ALL_LABELS),
            })

            label_idx += 1

with open(JSON_OUT, 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f'Extracted {label_idx} symbols → images/topografie/  +  topografie.json')
