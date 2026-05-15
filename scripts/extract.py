#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract.py — Generuje JS datové soubory z PDF podkladů pro Zálesák Trainer.
Spustit z kořene repozitáře: python3 scripts/extract.py

Zdroje:
  uploads/                  — základní materiály (žactvo)
  uploads/dorost/           — rozšířené materiály (dorost)
"""

import fitz
import base64, json, io, os, re, random
from PIL import Image

ROOT    = os.path.join(os.path.dirname(__file__), '..')
UPLOADS = os.path.join(ROOT, 'uploads')
DOROST  = os.path.join(ROOT, 'uploads', 'dorost')
OUTPUT  = os.path.join(ROOT, 'data')
os.makedirs(OUTPUT, exist_ok=True)

# ─────────────────────────── helpers ────────────────────────────────────────

def img_to_b64jpeg(img_bytes, max_px=480, quality=82):
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    w, h = img.size
    if max(w, h) > max_px:
        r = max_px / max(w, h)
        img = img.resize((int(w*r), int(h*r)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=quality, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()

def pil_to_b64jpeg(img, max_px=480, quality=82):
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    w, h = img.size
    if max(w, h) > max_px:
        r = max_px / max(w, h)
        img = img.resize((int(w*r), int(h*r)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=quality, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()

def to_key(name):
    name = name.lower().strip()
    for a, b in [('á','a'),('č','c'),('ď','d'),('é','e'),('ě','e'),('í','i'),
                 ('ň','n'),('ó','o'),('ř','r'),('š','s'),('ť','t'),('ú','u'),
                 ('ů','u'),('ý','y'),('ž','z')]:
        name = name.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '_', name).strip('_')

def make_options(correct, pool, n=4):
    distractors = [x for x in pool if x != correct]
    random.shuffle(distractors)
    opts = [correct] + distractors[:n-1]
    random.shuffle(opts)
    return opts

def write_js(filename, category, images_dict, questions_list):
    lines = [
        'var IMAGES_DATA=window.IMAGES_DATA||(window.IMAGES_DATA={});',
        'var QUESTIONS_DATA=window.QUESTIONS_DATA||(window.QUESTIONS_DATA={});',
        f'IMAGES_DATA["{category}"]={{',
    ]
    for key, b64 in images_dict.items():
        lines.append(f'"{key}":"{b64}",')
    lines += ['};', f'QUESTIONS_DATA["{category}"]=[']
    for q in questions_list:
        lines.append(json.dumps(q, ensure_ascii=False) + ',')
    lines.append('];')
    path = os.path.join(OUTPUT, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    kb = os.path.getsize(path) // 1024
    print(f'  ✓ {filename}  ({len(images_dict)} obrázků, {len(questions_list)} otázek, {kb} KB)')

# ─────────────────────────── tisk PDF extractor ─────────────────────────────

def extract_tisk_pdf(path, dorost_only=False):
    """
    Extrahuje (name, b64) páry z „tisk" PDF, kde je více obrázků na stránce.
    Každý obrázek má textový popisek těsně pod ním (offset ~50 px).
    dorost_only=True vrátí pouze položky označené „D " prefixem.
    """
    doc = fitz.open(path)
    entries = []   # (name, b64)

    for pi in range(doc.page_count):
        page = doc[pi]

        img_infos = page.get_image_info(xrefs=True)
        img_infos = [i for i in img_infos if i['width'] > 60 and i['height'] > 60]

        # Pozice obrázků: (cx, cy, xref)
        img_pos = [
            ((i['bbox'][0]+i['bbox'][2])/2,
             (i['bbox'][1]+i['bbox'][3])/2,
             i['xref'])
            for i in img_infos
        ]

        # Seskup slova do popisků podle blízkosti X a Y
        words = page.get_text('words')
        # quantize Y → stejný řádek
        line_map = {}
        for w in words:
            cy = round((w[1]+w[3])/2 / 5) * 5
            cx = (w[0]+w[2])/2
            line_map.setdefault(cy, []).append((cx, w[4]))

        # Ze slov na řádku sestav skupiny (oddělené mezerou >60 px)
        label_phrases = []  # (cx, cy, text)
        for cy in sorted(line_map):
            row = sorted(line_map[cy], key=lambda x: x[0])
            groups, cur = [], [row[0]]
            for w in row[1:]:
                if w[0] - cur[-1][0] < 70:
                    cur.append(w)
                else:
                    groups.append(cur)
                    cur = [w]
            groups.append(cur)
            for grp in groups:
                text = ' '.join(g[1] for g in grp).strip()
                if re.match(r'^\d{2}\.\d{2}\.\d{4}$', text) or re.match(r'^\d+$', text):
                    continue
                if text in ('•', ''):
                    continue
                gcx = sum(g[0] for g in grp) / len(grp)
                label_phrases.append((gcx, cy, text))

        # Ke každému popisku najdi nejbližší obrázek NAD ním
        used_xrefs = set()
        for lx, ly, label in label_phrases:
            # Přeskočit záhlaví sekcí (VERZÁLKY)
            if label.isupper() and not label.startswith('D '):
                continue

            is_dorost = label.startswith('D ')
            actual_name = label[2:].strip() if is_dorost else label.strip()

            if dorost_only and not is_dorost:
                continue

            # Nejbližší obrázek nad popiskem (obrázek.cy < popisek.cy, ΔY < 120, ΔX < 100)
            candidates = [
                (abs(icx - lx), ly - icy, xref)
                for icx, icy, xref in img_pos
                if icy < ly and (ly - icy) < 120 and xref not in used_xrefs
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda x: (x[0], x[1]))
            if candidates[0][0] > 100:
                continue

            xref = candidates[0][2]
            used_xrefs.add(xref)
            try:
                b64 = img_to_b64jpeg(doc.extract_image(xref)['image'], max_px=400)
            except Exception:
                continue
            entries.append((actual_name, b64))

    doc.close()
    return entries

# ─────────────────────────── animals ────────────────────────────────────────

def animal_question(name):
    lower = name.lower()
    if any(x in lower for x in ['candát','cejn','kapr','karas','lín','okoun',
                                  'pstruh','sumec','štika','úhoř']):
        return 'Co je tato ryba?'
    if any(x in lower for x in ['bažant','čáp','datel','havran','holub','husa',
                                  'kachna','káně','kos','kukačka','labuť','ledňáček',
                                  'racek','sojka','sokol','sova','straka','strakapoud',
                                  'sýkora','vlaštovka','volavka','vrabec','výr',
                                  'brhlík','červenka','hrdlička','kormorán','pěnkava',
                                  'poštolka','stehlík','sýček','špaček','zvonek']):
        return 'Co je tento pták?'
    if any(x in lower for x in ['čolek','ještěrka','mlok','ropucha','rosnička',
                                  'skokan','slepýš','užovka','zmije']):
        return 'Co je toto plaz nebo obojživelník?'
    return 'Co je toto zvíře?'

def extract_animals():
    print('\n📗 Přírodniny — zvířata (žactvo + dorost)')
    entries = []

    # Žactvo: jeden druh = jedna stránka
    doc = fitz.open(os.path.join(UPLOADS, 'Přírodniny - zvířata.pdf'))
    for i in range(1, doc.page_count):
        page = doc[i]
        text = page.get_text().strip().split('\n')[0].strip()
        if not text:
            continue
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        b64 = img_to_b64jpeg(doc.extract_image(imgs[0][0])['image'])
        entries.append((text, b64))
    doc.close()

    # Dorost: pouze D položky z tisk PDF
    new_d = extract_tisk_pdf(
        os.path.join(DOROST, 'ZZZ_přírodniny_ŽIVOČICHOVÉ (tisk).pdf'),
        dorost_only=True
    )
    print(f'  Dorost D živočichové: {len(new_d)} nových')
    for name, b64 in new_d:
        print(f'    + {name}')
    entries.extend(new_d)

    # Deduplikace podle jména
    seen, deduped = set(), []
    for name, b64 in entries:
        k = to_key(name)
        if k not in seen:
            seen.add(k)
            deduped.append((name, b64))
    entries = deduped

    names = [e[0] for e in entries]
    images, questions = {}, []
    for name, b64 in entries:
        key = to_key(name)
        images[key] = b64
        questions.append({'q': animal_question(name), 'img': f'prirodniny/{key}',
                          'a': name, 'options': make_options(name, names)})

    write_js('prirodniny.js', 'prirodniny', images, questions)

# ─────────────────────────── plants ─────────────────────────────────────────

HOUBY = {'babka','bedla','hadovka','hnojník','holubinka','hřib','klouzek','kotrč',
         'kozák','křemenáč','muchomůrka','ryzec','václavka','žampion',
         'čechratka','čirůvka','hlíva','pýchavka','suchohřib','špička'}

def plant_question(name):
    if any(h in name.lower() for h in HOUBY):
        return 'Co je tato houba?'
    return 'Co je tato rostlina?'

def extract_plants():
    print('\n🌿 Rostliny a houby (žactvo + dorost)')
    entries = []

    # Žactvo: jeden druh = jedna stránka
    doc = fitz.open(os.path.join(UPLOADS, 'rostliny - žactvo.pdf'))
    for i in range(1, doc.page_count):
        page = doc[i]
        lines = [l.strip() for l in page.get_text().strip().split('\n') if l.strip()]
        if not lines:
            continue
        name = ' '.join(lines[:2]).strip()
        name = re.sub(r'\s{2,}.*', '', name).strip()
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        b64 = img_to_b64jpeg(doc.extract_image(imgs[0][0])['image'])
        entries.append((name, b64))
    doc.close()

    # Dorost: pouze D položky z tisk PDF
    new_d = extract_tisk_pdf(
        os.path.join(DOROST, 'ZZZ_přírodniny_ROSTLINY (tisk).pdf'),
        dorost_only=True
    )
    print(f'  Dorost D rostliny: {len(new_d)} nových')
    for name, b64 in new_d:
        # Odstraň varianty za hlavním názvem: "- strom", "(květ)", "plod", apod.
        base = re.sub(r'[\s,]*[-–]?\s*(strom|keř|květ\.?|plod|list[a-z,. ]*)[\s,]*$', '', name, flags=re.I).strip()
        base = re.sub(r'\s*\(\s*(květ|plod|strom|list)\s*\)[\s,]*$', '', base, flags=re.I).strip()
        base = re.sub(r',\s*$', '', base).strip()
        # Odstraň případné zbytky "D název" uprostřed (artefakt z PDF)
        base = re.sub(r'\s+D\s+\w.*', '', base).strip()
        base = re.sub(r'\s+', ' ', base).strip()
        if not base:
            continue
        print(f'    + {base}')
        entries.append((base, b64))

    # Deduplikace podle klíče
    seen, deduped = set(), []
    for name, b64 in entries:
        k = to_key(name)
        if k not in seen:
            seen.add(k)
            deduped.append((name, b64))
    entries = deduped

    names = [e[0] for e in entries]
    images, questions = {}, []
    for name, b64 in entries:
        key = to_key(name)
        images[key] = b64
        questions.append({'q': plant_question(name), 'img': f'rostliny/{key}',
                          'a': name, 'options': make_options(name, names)})

    write_js('rostliny.js', 'rostliny', images, questions)

# ─────────────────────────── constellations ─────────────────────────────────

# Souhvězdí která jsou nová v dorost PDF (Hvězdy.pdf)
HVEZDY_NEW = {
    'Andromeda', 'Býk', 'Drak', 'Pegas', 'Perseus'
}
# Stránky v Hvězdy.pdf které přeskočit (více souhvězdí na jednom obrázku)
HVEZDY_SKIP_PAGES = {0, 5, 15, 16, 17, 18}  # celonebo mapa, multi-souhvězdí, roční mapy

def clean_constellation_name(text):
    """'1 Velký medvěd - Alkor,Mizar' → 'Velký medvěd'"""
    text = re.sub(r'^\d+\s*', '', text)          # odstraň číslo na začátku
    text = re.sub(r'\s*[-–(].*', '', text)        # odstraň " - ..." nebo " (..."
    return text.strip()

def extract_constellations():
    print('\n⭐ Souhvězdí (žactvo + dorost)')
    entries = []

    # Žactvo
    doc = fitz.open(os.path.join(UPLOADS, 'Souhvězdí žactvo.pdf'))
    for i in range(1, doc.page_count):
        page = doc[i]
        text = page.get_text().strip().split('\n')[0].strip()
        if not text:
            continue
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        b64 = img_to_b64jpeg(doc.extract_image(imgs[0][0])['image'])
        entries.append((text, b64))
    doc.close()

    # Dorost: nová souhvězdí z Hvězdy.pdf
    doc = fitz.open(os.path.join(DOROST, 'Hvězdy.pdf'))
    for i in range(doc.page_count):
        if i in HVEZDY_SKIP_PAGES:
            continue
        page = doc[i]
        raw_text = page.get_text().strip().split('\n')[0].strip()
        name = clean_constellation_name(raw_text)
        if not name or name not in HVEZDY_NEW:
            continue
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        b64 = img_to_b64jpeg(doc.extract_image(imgs[0][0])['image'])
        entries.append((name, b64))
        print(f'    + {name} (Hvězdy.pdf strana {i+1})')
    doc.close()

    # Deduplikace
    seen, deduped = set(), []
    for name, b64 in entries:
        k = to_key(name)
        if k not in seen:
            seen.add(k)
            deduped.append((name, b64))
    entries = deduped

    names = [e[0] for e in entries]
    images, questions = {}, []
    for name, b64 in entries:
        key = to_key(name)
        images[key] = b64
        questions.append({'q': 'Jak se jmenuje toto souhvězdí?',
                          'img': f'souhvezdi/{key}', 'a': name,
                          'options': make_options(name, names)})

    write_js('souhvezdi.js', 'souhvezdi', images, questions)

# ─────────────────────────── mistopis ───────────────────────────────────────

def extract_mistopis():
    print('\n🏰 Mistopis / Dominanty')
    doc = fitz.open(os.path.join(UPLOADS, 'mistopis.pdf'))
    entries = []

    for pi in range(doc.page_count):
        page = doc[pi]
        words = page.get_text('words')

        line_map = {}
        for w in words:
            cy = round((w[1]+w[3])/2 / 5) * 5
            cx = (w[0]+w[2])/2
            line_map.setdefault(cy, []).append((cx, w[4]))

        raw_labels = []
        for cy in sorted(line_map):
            row = sorted(line_map[cy], key=lambda x: x[0])
            groups, cur = [], [row[0]]
            for w in row[1:]:
                if w[0] - cur[-1][0] < 70:
                    cur.append(w)
                else:
                    groups.append(cur)
                    cur = [w]
            groups.append(cur)
            for grp in groups:
                text = ' '.join(g[1] for g in grp).strip()
                if re.match(r'^\d{2}\.\d{2}\.\d{4}$', text) or re.match(r'^\d+$', text):
                    continue
                gcx = sum(g[0] for g in grp) / len(grp)
                raw_labels.append({'cx': gcx, 'cy': cy, 'txt': text})

        # Slouč blízké popisky (±80 X, ±40 Y)
        used, merged = set(), []
        raw_labels.sort(key=lambda x: (round(x['cx']/80), x['cy']))
        for i, lb in enumerate(raw_labels):
            if i in used:
                continue
            group = [lb]; used.add(i)
            for j, lb2 in enumerate(raw_labels):
                if j in used:
                    continue
                if abs(lb2['cx']-lb['cx']) < 80 and abs(lb2['cy']-lb['cy']) < 40:
                    group.append(lb2); used.add(j)
            txt = ' '.join(g['txt'] for g in sorted(group, key=lambda x: x['cy']))
            txt = re.sub(r'\s+', ' ', txt).strip()
            cx = sum(g['cx'] for g in group)/len(group)
            cy = sum(g['cy'] for g in group)/len(group)
            merged.append({'cx': cx, 'cy': cy, 'txt': txt})

        img_infos = page.get_image_info(xrefs=True)
        img_infos = [i for i in img_infos if i['width'] > 80 and i['height'] > 80]

        for img_info in img_infos:
            bbox = img_info['bbox']
            img_cx = (bbox[0]+bbox[2])/2
            img_cy = (bbox[1]+bbox[3])/2
            y_lo, y_hi = bbox[1]-10, bbox[3]+10
            candidates = [lb for lb in merged if y_lo <= lb['cy'] <= y_hi]
            if not candidates:
                candidates = [lb for lb in merged if abs(lb['cy']-img_cy) < 120]
            if not candidates:
                continue
            best = min(candidates, key=lambda lb: abs(lb['cx']-img_cx))
            label = re.sub(r'\s*[-–]\s*', ' – ', best['txt'])
            label = re.sub(r'\s+', ' ', label).strip()
            try:
                b64 = img_to_b64jpeg(doc.extract_image(img_info['xref'])['image'], max_px=400)
            except Exception:
                continue
            entries.append((label, b64))

    doc.close()
    seen = {}
    for name, b64 in entries:
        if name not in seen:
            seen[name] = b64
    entries = list(seen.items())
    print(f'  Unikátních dominant: {len(entries)}')

    names = [e[0] for e in entries]
    images, questions = {}, []
    for name, b64 in entries:
        key = to_key(name)
        images[key] = b64
        questions.append({'q': 'Jak se jmenuje toto místo nebo dominanta?',
                          'img': f'dominanty/{key}', 'a': name,
                          'options': make_options(name, names)})
    write_js('dominanty.js', 'dominanty', images, questions)

# ─────────────────────────── map signs ──────────────────────────────────────

MAP_LABELS_P1 = [
    'Zpevněná cesta', 'Pěšina', 'Polní a lesní cesta',
    'Trasa vodní dopravy', 'Silnice 1. třídy', 'Ostatní silnice',
    'Dálnice', 'Násep', 'Řeka s jezerem',
    'Řeka s mostem', 'Řeka s přívozem', 'Pramen',
    'Kostel', 'Meteorologická stanice', 'Pomník',
    'Pevnost', 'Zřícenina hradu', 'Veřejné tábořiště',
    'Autokemping', 'Ohniště, stánek, tůz', 'NTZ (noclehárna, tábořiště, zázemí)',
    'Vodní mlýn', 'Rozhledna', 'Orientačně důležitý strom',
]
MAP_LABELS_P2 = [
    'Muzeum, galerie', 'Hraniční přechod', 'Hraniční přechod pro pěší a cyklisty',
    'Kulturně pozoruhodné místo', 'Ubytovna', 'Hotel',
    'Stanice horské služby', 'Restaurace', 'Hranice CHKO',
    'Hranice národního parku', 'Hranice přírodního parku', 'Přírodní zajímavost',
    'Sad a zahrada', 'Vinice', 'Porosty křoví',
    'Chmelnice', 'Vodojem', 'Pramen (studánka)',
    'Veřejné koupaliště', 'Studna', 'Elektrárna',
    'Hájovna, myslivna', 'Továrna s komínem', 'Samostatná budova',
]
COL_SPLITS_2X   = [46, 196, 338, 482]
ROW_SPLITS_P1_2X = [153, 282, 348, 455, 558, 700, 840, 950, 1065]
ROW_SPLITS_P2_2X = [108, 258, 392, 526, 594, 770, 920, 1062, 1175]

def extract_map_signs():
    print('\n🗺️  Mapové značky')
    doc = fitz.open(os.path.join(UPLOADS, 'Mapové značky 2019.pdf'))
    all_labels = MAP_LABELS_P1 + MAP_LABELS_P2
    page_configs = [
        (0, ROW_SPLITS_P1_2X, MAP_LABELS_P1),
        (1, ROW_SPLITS_P2_2X, MAP_LABELS_P2),
    ]
    images, questions = {}, []
    for page_idx, row_splits, labels in page_configs:
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        sym_idx = 0
        for row in range(len(row_splits)-1):
            y0, y1 = row_splits[row], row_splits[row+1]
            for col in range(len(COL_SPLITS_2X)-1):
                x0, x1 = COL_SPLITS_2X[col], COL_SPLITS_2X[col+1]
                if sym_idx >= len(labels):
                    break
                name = labels[sym_idx]
                key  = to_key(name)
                b64  = pil_to_b64jpeg(img.crop((x0, y0, x1, y1)), max_px=200, quality=85)
                images[key] = b64
                questions.append({'q': 'Co označuje tato mapová značka?',
                                   'img': f'topografie/{key}', 'imgClass': 'topo',
                                   'a': name, 'options': make_options(name, all_labels)})
                sym_idx += 1
    doc.close()
    write_js('topografie.js', 'topografie', images, questions)

# ─────────────────────────── knot images ────────────────────────────────────

UZLY_PAGES = [
    (0, 'Lodní uzel'),
    (1, 'Očková spojka (UIAA)'),
    (2, 'Škotová spojka'),
    (3, 'Osmičkový uzel'),
    (4, 'Zkracovačka'),
]

def extract_knot_images():
    """Extrahuje obrázky uzlů z PDF — vrátí (name, b64) páry."""
    path = os.path.join(DOROST, 'ZZZ_uzly_žp.pdf')
    doc = fitz.open(path)
    entries = []
    for page_idx, name in UZLY_PAGES:
        if page_idx >= doc.page_count:
            continue
        page = doc[page_idx]
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        # Vezmi prostřední obrázek (ukazuje hotový uzel)
        mid = len(imgs) // 2
        try:
            b64 = img_to_b64jpeg(doc.extract_image(imgs[mid][0])['image'], max_px=400)
            entries.append((name, b64))
            print(f'    + {name}')
        except Exception:
            pass
    doc.close()
    return entries

# ─────────────────────────── text questions ──────────────────────────────────

def write_text_questions():
    print('\n📝 Textové otázky')

    # ── Uzly (text + obrázky) ────────────────────────────────────────────────
    print('  Extrahuji obrázky uzlů...')
    knot_entries = extract_knot_images()
    knot_names = [e[0] for e in knot_entries]
    knot_images = {}
    knot_img_questions = []
    for name, b64 in knot_entries:
        key = to_key(name)
        knot_images[key] = b64
        knot_img_questions.append({
            'q': 'Jak se jmenuje tento uzel?',
            'img': f'uzly/{key}',
            'a': name,
            'options': make_options(name, knot_names)
        })

    uzly_text = [
        {'q':'Jak se jmenuje uzel tvořící pevnou smyčku, která se neutahuje?','a':'Lodní uzel','options':['Lodní uzel','Osmičkový uzel','Tesařský uzel','Dračí smyčka']},
        {'q':'Jaký uzel se používá ke spojování dvou lan stejné tloušťky?','a':'Plochý uzel (čtvercový)','options':['Plochý uzel (čtvercový)','Lodní uzel','Lodní smyčka','Alpský motýl']},
        {'q':'Jak se nazývá uzel ve tvaru číslice 8?','a':'Osmičkový uzel','options':['Osmičkový uzel','Plochý uzel','Tesařský uzel','Prusíkův uzel']},
        {'q':'Jaký uzel se váže na tyč nebo kůl pro upevnění lana?','a':'Tesařský uzel','options':['Tesařský uzel','Lodní uzel','Plochý uzel','Zkracovačka']},
        {'q':'Jak se jmenuje uzel pro zkrácení lana bez stříhání?','a':'Zkracovačka','options':['Zkracovačka','Alpský motýl','Prusíkův uzel','Dračí smyčka']},
        {'q':'Jaký uzel umožňuje posunování po napnutém laně (třecí uzel)?','a':'Prusíkův uzel','options':['Prusíkův uzel','Zkracovačka','Osmičkový uzel','Tesařský uzel']},
        {'q':'Jak se jmenuje uzel pro spojení dvou lan různých tlouštěk?','a':'Škotová spojka','options':['Škotová spojka','Plochý uzel','Alpský motýl','Lodní uzel']},
        {'q':'Jaký uzel zálesáci používají jako základní spojovací uzel?','a':'Plochý uzel (čtvercový)','options':['Plochý uzel (čtvercový)','Osmičkový uzel','Alpský motýl','Lodní uzel']},
        {'q':'Jak se jmenuje uzel tvořící pevnou smyčku uprostřed lana?','a':'Alpský motýl','options':['Alpský motýl','Lodní uzel','Osmičkový uzel','Rybářský uzel']},
        {'q':'Jaký uzel tuhne při zatížení a je samosvěrný?','a':'Prusíkův uzel','options':['Prusíkův uzel','Zkracovačka','Tesařský uzel','Dračí smyčka']},
        {'q':'Jak se jmenuje horolezecký uzel pro jistění na laně (UIAA)?','a':'Očková spojka (UIAA)','options':['Očková spojka (UIAA)','Osmičkový uzel','Prusíkův uzel','Plochý uzel']},
        {'q':'Jaký uzel se používá pro napínání šňůry tábora nebo stanu?','a':'Tesařský uzel','options':['Tesařský uzel','Lodní uzel','Plochý uzel','Alpský motýl']},
        {'q':'Jak se jmenuje nejzákladnější horolezecký uzel pro připevnění k laně?','a':'Osmičkový uzel','options':['Osmičkový uzel','Plochý uzel','Lodní uzel','Prusíkův uzel']},
        {'q':'Jaký uzel použiješ pro spojení lana s karabinou nebo kůlem?','a':'Lodní uzel','options':['Lodní uzel','Škotová spojka','Prusíkův uzel','Zkracovačka']},
    ]
    uzly = uzly_text + knot_img_questions

    # ── Zdravověda ────────────────────────────────────────────────────────────
    zdravoveda = [
        # Anatomie
        {'q':'Kolik máme krčních obratlů?','a':'7','options':['7','5','9','12']},
        {'q':'Kde je uloženo srdce?','a':'V hrudním koši nalevo pod hrudní kostí','options':['V hrudním koši nalevo pod hrudní kostí','V dutině břišní','V pravé části hrudníku','Pod levou lopatkou']},
        {'q':'Kolik stahů za minutu provede srdce průměrného zdravého dospělého?','a':'72–76','options':['72–76','50–55','90–100','110–120']},
        {'q':'Kolik litrů krve má průměrný dospělý člověk?','a':'5–6 litrů','options':['5–6 litrů','2–3 litry','8–10 litrů','1–2 litry']},
        {'q':'Jaká je funkce červených krvinek?','a':'Přenášejí kyslík od srdce a odvádějí CO₂ zpět','options':['Přenášejí kyslík od srdce a odvádějí CO₂ zpět','Bojují s infekcemi','Srážejí krev','Produkují hormony']},
        # Krvácení
        {'q':'Které krvácení je pro člověka nejnebezpečnější?','a':'Vnitřní (nelze hned poznat)','options':['Vnitřní (nelze hned poznat)','Tepenné','Žilní','Kapilární']},
        {'q':'Kam přikládáme škrtidlo při masivním krvácení z končetiny?','a':'Nad ránu, blíže k srdci, ne v blízkosti kloubu','options':['Nad ránu, blíže k srdci, ne v blízkosti kloubu','Pod ránu, co nejdále od srdce','Přímo na ránu','Na nejbližší kloub']},
        {'q':'Jakým obvazem nejlépe zastavíme masivní krvácení?','a':'Tlakovým obvazem','options':['Tlakovým obvazem','Obinadlem','Trojcípým šátkem','Škrtidlem přes ránu']},
        {'q':'Co provedeme s postiženým při krvácení z nosu?','a':'Posadíme v předklonu, za krk studený obklad','options':['Posadíme v předklonu, za krk studený obklad','Položíme na záda a zakloníme hlavu','Posadíme v záklonu','Stlačíme nosní křídla a zakloníme hlavu']},
        # Bezvědomí a dýchání
        {'q':'Čím je ohrožen postižený při bezvědomí?','a':'Zadušením — je třeba zprůchodnit dýchací cesty','options':['Zadušením — je třeba zprůchodnit dýchací cesty','Vykrvácením','Podchlazením','Proleženinami']},
        {'q':'K čemu slouží záklon hlavy a předsunutí dolní čelisti?','a':'K uvolnění a zprůchodnění dýchacích cest','options':['K uvolnění a zprůchodnění dýchacích cest','K zástavě krvácení z nosu','K stabilizaci páteře','K podání umělého dýchání']},
        {'q':'Co podáme postiženému diabetikovi s příznaky hypoglykémie (opocení, malátnost)?','a':'Rychlý cukr — sladký nápoj nebo hroznový cukr','options':['Rychlý cukr — sladký nápoj nebo hroznový cukr','Vodu','Inzulín','Nic — čekáme na záchranku']},
        {'q':'Jaké jsou příznaky šoku po zlomenině velké kosti?','a':'Bledost, lepkavé pocení, dezorientace, malátnost','options':['Bledost, lepkavé pocení, dezorientace, malátnost','Horečka a třesavka','Silné krvácení z rány','Otok a modřina']},
        {'q':'Do jaké polohy uložíme dýchající osobu v bezvědomí?','a':'Do stabilizované (zotavovací) polohy na boku','options':['Do stabilizované (zotavovací) polohy na boku','Na záda','Na břicho','Do sedu']},
        {'q':'Jak zastavíme silné krvácení z končetiny?','a':'Přímým tlakem na ránu, případně turniketem','options':['Přímým tlakem na ránu, případně turniketem','Zvedneme končetinu nahoru','Přiložíme led','Necháme ránu otevřenou']},
        # Poranění páteře, popáleniny, omrzliny
        {'q':'Jaké jsou příznaky poranění páteře?','a':'Bolest, ztráta hybnosti, mravenčení nebo necitlivost končetin','options':['Bolest, ztráta hybnosti, mravenčení nebo necitlivost končetin','Pouze silná bolest zad','Otoky a modřiny','Nevolnost a zvracení']},
        {'q':'Co použijeme při popáleninách k první pomoci?','a':'Vlažnou až studenou tekoucí vodu (ne ledovou), 10–20 minut','options':['Vlažnou až studenou tekoucí vodu (ne ledovou), 10–20 minut','Máslo nebo olej','Led nebo studené obklady','Suchou tkaninu bez ochlazení']},
        {'q':'Která místa jsou nejčastěji ohrožena omrzlinami?','a':'Okrajové části těla — prsty, nos, uši, brada','options':['Okrajové části těla — prsty, nos, uši, brada','Záda a hrudník','Stehna a lýtka','Lokte a kolena']},
        # KPR
        {'q':'Jak hluboko stlačujeme hrudník při KPR u dospělého?','a':'5–6 cm','options':['5–6 cm','2–3 cm','8–10 cm','1–2 cm']},
        {'q':'Jaký je poměr stlačení ku vdechům při KPR (dospělý, 1 zachránce)?','a':'30 : 2','options':['30 : 2','15 : 2','5 : 1','10 : 2']},
        {'q':'V jakém rytmu stlačujeme hrudník při KPR?','a':'100–120 stlačení za minutu','options':['100–120 stlačení za minutu','60–80 za minutu','140–160 za minutu','50–60 za minutu']},
        {'q':'Co je Gasping?','a':'Lapavé dýchání v časných okamžicích náhlé zástavy oběhu','options':['Lapavé dýchání v časných okamžicích náhlé zástavy oběhu','Normální hluboké dýchání','Příznak astmatického záchvatu','Druh umělého dýchání']},
        {'q':'Kdy zahajujeme resuscitaci (KPR)?','a':'Při poruše vědomí, dýchání nebo srdeční činnosti','options':['Při poruše vědomí, dýchání nebo srdeční činnosti','Pouze při zástavě srdce','Pouze při zástavě dechu','Vždy při bezvědomí bez ohledu na dýchání']},
        {'q':'Na jaké číslo voláme záchrannou službu v ČR?','a':'155','options':['155','112','150','158']},
        {'q':'Co je Rescue point (bod záchrany v terénu)?','a':'Místo označené tabulkou s unikátním kódem pro přesnou lokalizaci záchranky','options':['Místo označené tabulkou s unikátním kódem pro přesnou lokalizaci záchranky','Záchranná stanice horské služby','Heliport pro záchranný vrtulník','Lékárnička umístěná v terénu']},
        {'q':'Jak správně vytáhnout přisáté klíště?','a':'Speciálními kleštěmi co nejblíže kůži, otáčivým pohybem','options':['Speciálními kleštěmi co nejblíže kůži, otáčivým pohybem','Přiložíme zápalku','Potřeme olejem','Překryjeme náplastí a počkáme']},
        {'q':'Co uděláme s popáleninou bezprostředně po poranění?','a':'Chladíme tekoucí vodou 10–20 minut','options':['Chladíme tekoucí vodou 10–20 minut','Potřeme máslem','Propíchneme puchýře','Zabalíme do suché tkaniny']},
        {'q':'Jak poznáme přehřátí (úpal)?','a':'Horká suchá kůže, vysoká teplota, zmatenost','options':['Horká suchá kůže, vysoká teplota, zmatenost','Studená vlhká kůže, třesavka','Bolest břicha, nevolnost','Bledost a mdloby']},
        {'q':'Co uděláme jako první při nálezu bezvědomé osoby?','a':'Ověříme reakci a dech, zavoláme 155','options':['Ověříme reakci a dech, zavoláme 155','Zahájíme KPR','Dáme postiženého do sedu','Podáme vodu']},
        {'q':'Jak znehybníme zlomeninu v terénu bez dílen?','a':'Přivážeme k rovné tyči nebo pevnému předmětu','options':['Přivážeme k rovné tyči nebo pevnému předmětu','Pevně zavineme do obvazu','Necháme volně','Přiložíme studený obklad']},
    ]

    # ── Historie ──────────────────────────────────────────────────────────────
    historie = [
        {'q':'Ve kterém roce byl založen Sokol?','a':'1862','options':['1862','1848','1878','1900']},
        {'q':'Která sokolská jednota vznikla jako první?','a':'Tělocvičná jednota pražská','options':['Tělocvičná jednota pražská','Sokol Brno','Orel Praha','Jungmannova jednota']},
        {'q':'Jak se jmenovali dva hlavní zakladatelé Sokola?','a':'Miroslav Tyrš a Jindřich Fügner','options':['Miroslav Tyrš a Jindřich Fügner','Josef Scheiner a Karel Havlíček','Jan Neruda a Bedřich Smetana','František Palacký a Tomáš Masaryk']},
        {'q':'Jakou funkci zastával Miroslav Tyrš v Sokole?','a':'Náčelník (místostarosta)','options':['Náčelník (místostarosta)','Starosta','Pokladník','Jednatel']},
        {'q':'Kdo byl Jindřich Fügner?','a':'Zakladatel a první starosta Sokola','options':['Zakladatel a první starosta Sokola','První náčelník Sokola','Sokolský básník','Zakladatel Orla']},
        {'q':'Kde se konal první sokolský slet?','a':'V Praze na Střeleckém ostrově','options':['V Praze na Střeleckém ostrově','V Brně na Lužánkách','V Plzni','V Olomouci']},
        {'q':'Kdy se konal první sokolský slet?','a':'18. června 1882','options':['18. června 1882','1. května 1862','27. dubna 1880','15. března 1890']},
        {'q':'Jaké bylo cílové místo prvního sokolského výletu?','a':'Hora Říp','options':['Hora Říp','Blaník','Sněžka','Křivoklát']},
        {'q':'V kterém roce se uskutečnil první sokolský výlet?','a':'27. dubna 1862','options':['27. dubna 1862','18. června 1882','1. května 1870','15. března 1848']},
        {'q':'Kdo byla Klemeňa Hanušová?','a':'Spoluzakladatelka Tělocvičného spolku paní a dívek pražských','options':['Spoluzakladatelka Tělocvičného spolku paní a dívek pražských','První náčelnice ČOS','Manželka Miroslava Tyrše','Zakladatelka dívčího Sokola v Brně']},
        {'q':'Ve kterém roce vystoupily ženy poprvé na sletu?','a':'1901','options':['1901','1882','1920','1907']},
        {'q':'Ve kterém roce poprvé vystoupilo na sletu žactvo?','a':'1907','options':['1907','1882','1901','1920']},
        {'q':'Jak zní sokolský pozdrav?','a':'Nazdar','options':['Nazdar','Zdar','Na zdar bratře','Ahoj']},
        {'q':'Která mužská skladba X. sletu byla reakcí na politiku v Evropě?','a':'Přísaha republice','options':['Přísaha republice','Vpřed za vlast','Sokolský pochod','Věrni zůstaneme']},
        {'q':'Kolik cvičenců vystoupilo ve skladbě Přísaha republice na X. sletu?','a':'30 000','options':['30 000','10 000','50 000','5 000']},
        {'q':'Jak se nazývaly bojové útvary v 1. světové válce přispívající ke vzniku ČR?','a':'Československé legie','options':['Československé legie','Sokolské brigády','Domobrana','Husité']},
        {'q':'Kdo byla Marie Provazníková?','a':'Náčelnice ČOS, po emigraci pomohla založit Ústředí čs. sokolstva v zahraničí','options':['Náčelnice ČOS, po emigraci pomohla založit Ústředí čs. sokolstva v zahraničí','Manželka Tyrše','Zakladatelka ženského Sokola','Starostka ČOS']},
        {'q':'Ve kterém roce byl slavnostně otevřen Tyršův dům?','a':'1925','options':['1925','1900','1938','1948']},
        {'q':'Který den je „Památný den Sokola"?','a':'8. října','options':['8. října','28. října','1. května','17. listopadu']},
        {'q':'Co si připomínáme Památným dnem sokolstva?','a':'Akci Sokol — likvidaci Sokola nacisty v noci ze 7. na 8. října 1941','options':['Akci Sokol — likvidaci Sokola nacisty v noci ze 7. na 8. října 1941','Vznik Sokola v roce 1862','První sokolský slet','Obnovení Sokola po roce 1989']},
        {'q':'Kde zahynul zakladatel Sokola Miroslav Tyrš?','a':'V rakouském Oetzu — utonul v říčce Ache','options':['V rakouském Oetzu — utonul v říčce Ache','V Alpách při výstupu','V Praze při nehodě','Na Šumavě']},
        {'q':'Kde se konal první přebor ČOS v Zálesáckém závodě zdatnosti?','a':'Jurenkova osada u Třebíče','options':['Jurenkova osada u Třebíče','Praha — Stromovka','Brno — Lužánky','Plzeň']},
        {'q':'Co znamená zkratka ČOS?','a':'Česká obec sokolská','options':['Česká obec sokolská','Česká organizace sportu','Český odbor sokolství','Celostátní obnova Sokola']},
        {'q':'Jak se jmenuje starosta ČOS?','a':'Martin Chlumský','options':['Martin Chlumský','Petr Sádek','Kateřina Machů','Josef Scheiner']},
        {'q':'Jak se jmenuje náčelník ČOS?','a':'Petr Sádek','options':['Petr Sádek','Martin Chlumský','Kateřina Machů','Zdeněk Lauschmann']},
        {'q':'Jak se jmenuje náčelnice ČOS?','a':'Kateřina Machů','options':['Kateřina Machů','Marie Provazníková','Klemeňa Hanušová','Jana Nováková']},
        {'q':'Jaké tři programové útvary má ČOS?','a':'Odbor všestrannosti, Odbor sportu, Odbor kulturní','options':['Odbor všestrannosti, Odbor sportu, Odbor kulturní','Odbor mládeže, Odbor dospělých, Odbor seniorů','Odbor zálesáků, Odbor gymnastek, Odbor atletů','Odbor vzdělávání, Odbor sportu, Odbor zálesáků']},
        {'q':'Co je Tyršův dům?','a':'Barokní areál na Malé Straně — sídlo České obce sokolské','options':['Barokní areál na Malé Straně — sídlo České obce sokolské','Muzeum Sokola v Brně','Sokolská tělocvična v Plzni','Letní tábor Sokola']},
        {'q':'Co znamená slovo „kalokagathia"?','a':'Antický ideál souladu tělesné krásy, zdatnosti a morální ušlechtilosti','options':['Antický ideál souladu tělesné krásy, zdatnosti a morální ušlechtilosti','Řecký bůh sportu','Sokolský cvičební systém','Druh sokolského pozdravu']},
        {'q':'Co jsou sokolské „šibřinky"?','a':'Tradiční sokolské maškarní plesy v době masopustu','options':['Tradiční sokolské maškarní plesy v době masopustu','Letní sokolský tábor','Sokolský výlet do přírody','Cvičební skladba na sletu']},
        {'q':'Kdo byl prvním vedoucím komise pobytu v přírodě po roce 1990?','a':'Zdeněk Lauschmann','options':['Zdeněk Lauschmann','Martin Chlumský','Petr Sádek','Josef Scheiner']},
        {'q':'Jaký vztah měl A. B. Svojsík k Sokolu?','a':'Byl náčelník Sokola, pak vytvořil vlastní skautskou organizaci','options':['Byl náčelník Sokola, pak vytvořil vlastní skautskou organizaci','Byl zakládajícím členem Sokola','Byl starosta ČOS','Sokol nikdy nenavštívil']},
        {'q':'Co znamená zkratka PP v náčelnictvu ČOS?','a':'Komise pobytu v přírodě','options':['Komise pobytu v přírodě','Pohybová průprava','Pedagogická příprava','Přírodnický program']},
        {'q':'Podle koho byl Sokol pojmenován?','a':'Podle jihoslovanských bojovníků za svébytnost — sokolů','options':['Podle jihoslovanských bojovníků za svébytnost — sokolů','Podle dravého ptáka sokola','Podle zakladatele Tyrše','Podle Jana Nerudy']},
        {'q':'Kdo napsal pojednání „Náš úkol, směr a cíl"?','a':'Miroslav Tyrš','options':['Miroslav Tyrš','Jindřich Fügner','Josef Scheiner','Klemeňa Hanušová']},
        {'q':'Jak se jmenuje vzdělávací útvar ČOS?','a':'Ústřední škola České obce sokolské','options':['Ústřední škola České obce sokolské','Akademie Sokola','Sokolský institut','Tyrš akademie']},
        {'q':'Jak se jmenuje základní právní předpis ČOS?','a':'Stanovy České obce sokolské','options':['Stanovy České obce sokolské','Ústava Sokola','Zákon o Sokole','Řád sokolský']},
        {'q':'Na co odkazuje sokolské heslo „Tužme se"?','a':'Na heslo Miroslava Tyrše — tužme se fyzicky i duševně','options':['Na heslo Miroslava Tyrše — tužme se fyzicky i duševně','Na sokolský pochod','Na první slet','Na bojový pokřik sokolů']},
        {'q':'Co je sokolský slet?','a':'Celostátní hromadné cvičební vystoupení sokolů','options':['Celostátní hromadné cvičební vystoupení sokolů','Sokolský výlet do přírody','Zálesácký závod zdatnosti','Sokolský ples']},
    ]

    # Zapiš text_questions.js (bez uzlových obrázků — ty jsou v uzly.js)
    lines = [
        'var QUESTIONS_DATA=window.QUESTIONS_DATA||(window.QUESTIONS_DATA={});',
        f'QUESTIONS_DATA["uzly"]=(QUESTIONS_DATA["uzly"]||[]).concat({json.dumps(uzly_text, ensure_ascii=False)});',
        f'QUESTIONS_DATA["zdravoveda"]={json.dumps(zdravoveda, ensure_ascii=False)};',
        f'QUESTIONS_DATA["historie"]={json.dumps(historie, ensure_ascii=False)};',
    ]
    path = os.path.join(OUTPUT, 'text_questions.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    kb = os.path.getsize(path) // 1024
    print(f'  ✓ text_questions.js  (uzly_text:{len(uzly_text)}, zdravoveda:{len(zdravoveda)}, historie:{len(historie)}, {kb} KB)')

    # Zapiš uzly.js (obrázky + obrázkové otázky)
    lines2 = [
        'var IMAGES_DATA=window.IMAGES_DATA||(window.IMAGES_DATA={});',
        'var QUESTIONS_DATA=window.QUESTIONS_DATA||(window.QUESTIONS_DATA={});',
        f'IMAGES_DATA["uzly"]={{',
    ]
    for name, b64 in knot_entries:
        lines2.append(f'"{to_key(name)}":"{b64}",')
    lines2 += ['};',
               f'QUESTIONS_DATA["uzly"]=(QUESTIONS_DATA["uzly"]||[]).concat({json.dumps(knot_img_questions, ensure_ascii=False)});']
    path2 = os.path.join(OUTPUT, 'uzly.js')
    with open(path2, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines2))
    kb2 = os.path.getsize(path2) // 1024
    print(f'  ✓ uzly.js  ({len(knot_entries)} obrázků, {len(knot_img_questions)} otázek, {kb2} KB)')

# ─────────────────────────── main ───────────────────────────────────────────

if __name__ == '__main__':
    random.seed(42)
    print('=== Zálesák Trainer — extrakce dat ===')
    extract_animals()
    extract_plants()
    extract_constellations()
    extract_mistopis()
    extract_map_signs()
    write_text_questions()
    print('\n✅ Hotovo! Soubory jsou v adresáři data/')
