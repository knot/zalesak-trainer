#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract.py — Generuje JS datové soubory z PDF podkladů pro Zálesák Trainer.
Spustit z kořene repozitáře: python3 scripts/extract.py
"""

import fitz
import base64, json, io, os, re, random
from PIL import Image

UPLOADS = os.path.join(os.path.dirname(__file__), '..', 'uploads')
OUTPUT  = os.path.join(os.path.dirname(__file__), '..', 'data')
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
    return random.sample([correct] + distractors[:n-1], min(n, len(distractors)+1))

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

# ─────────────────────────── animals ────────────────────────────────────────

def extract_animals():
    print('\n📗 Přírodniny — zvířata')
    doc = fitz.open(os.path.join(UPLOADS, 'Přírodniny - zvířata.pdf'))
    entries = []

    for i in range(1, doc.page_count):
        page = doc[i]
        text = page.get_text().strip().split('\n')[0].strip()
        if not text:
            continue
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        img_bytes = doc.extract_image(imgs[0][0])['image']
        entries.append((text, img_to_b64jpeg(img_bytes)))

    doc.close()
    names = [e[0] for e in entries]
    images, questions = {}, []

    for name, b64 in entries:
        key = to_key(name)
        images[key] = b64
        lower = name.lower()
        if any(x in lower for x in ['candát','cejn','kapr','karas','lín','okoun',
                                      'pstruh','sumec','štika','úhoř']):
            q = 'Co je tato ryba?'
        elif any(x in lower for x in ['babočka','bělásek']):
            q = 'Co je tento motýl?'
        elif any(x in lower for x in ['bažant','čáp','datel','havran','holub','husa',
                                       'kachna','káně','kos','kukačka','labuť','ledňáček',
                                       'racek','sojka','sokol','sova','straka','strakapoud',
                                       'sýkora','vlaštovka','volavka','vrabec','výr']):
            q = 'Co je tento pták?'
        elif any(x in lower for x in ['čolek','ještěrka','mlok','ropucha','rosnička',
                                       'skokan','slepýš','užovka','zmije']):
            q = 'Co je toto plaz nebo obojživelník?'
        else:
            q = 'Co je toto zvíře?'
        questions.append({'q': q, 'img': f'prirodniny/{key}', 'a': name,
                          'options': make_options(name, names)})

    write_js('prirodniny.js', 'prirodniny', images, questions)

# ─────────────────────────── plants ─────────────────────────────────────────

def extract_plants():
    print('\n🌿 Rostliny')
    doc = fitz.open(os.path.join(UPLOADS, 'rostliny - žactvo.pdf'))
    entries = []
    HOUBY = {'babka','bedla','hadovka','hnojník','holubinka','hřib',
              'klouzek','kotrč','kozák','křemenáč','muchomůrka','ryzec','václavka','žampion'}

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
        img_bytes = doc.extract_image(imgs[0][0])['image']
        entries.append((name, img_to_b64jpeg(img_bytes)))

    doc.close()
    names = [e[0] for e in entries]
    images, questions = {}, []

    for name, b64 in entries:
        key = to_key(name)
        images[key] = b64
        is_mushroom = any(h in name.lower() for h in HOUBY)
        q = 'Co je tato houba?' if is_mushroom else 'Co je tato rostlina?'
        questions.append({'q': q, 'img': f'rostliny/{key}', 'a': name,
                          'options': make_options(name, names)})

    write_js('rostliny.js', 'rostliny', images, questions)

# ─────────────────────────── constellations ─────────────────────────────────

def extract_constellations():
    print('\n⭐ Souhvězdí')
    doc = fitz.open(os.path.join(UPLOADS, 'Souhvězdí žactvo.pdf'))
    entries = []

    for i in range(1, doc.page_count):
        page = doc[i]
        text = page.get_text().strip().split('\n')[0].strip()
        if not text:
            continue
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        img_bytes = doc.extract_image(imgs[0][0])['image']
        entries.append((text, img_to_b64jpeg(img_bytes)))

    doc.close()
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
    entries = []   # (label, b64)

    for pi in range(doc.page_count):
        page = doc[pi]

        # Collect words and group by proximity into labels with X,Y positions
        words = page.get_text('words')  # (x0,y0,x1,y1,word,block,line,word_no)
        # Group words on same line (Y within 8pt), then merge nearby lines in same column
        lines_raw = {}
        for w in words:
            cx = (w[0]+w[2])/2
            cy = (w[1]+w[3])/2
            txt = w[4].strip()
            if not txt or re.match(r'^\d{2}\.\d{2}\.\d{4}$', txt) or re.match(r'^\d+$', txt):
                continue
            key_y = round(cy / 10) * 10
            key_x = round(cx / 80) * 80
            k = (key_x, key_y)
            if k not in lines_raw:
                lines_raw[k] = {'words': [], 'cx_sum': 0, 'cy_sum': 0, 'count': 0}
            lines_raw[k]['words'].append(txt)
            lines_raw[k]['cx_sum'] += cx
            lines_raw[k]['cy_sum'] += cy
            lines_raw[k]['count'] += 1

        # Convert to flat list of (cx, cy, text)
        raw_labels = []
        for k, v in lines_raw.items():
            txt = ' '.join(v['words'])
            cx = v['cx_sum'] / v['count']
            cy = v['cy_sum'] / v['count']
            raw_labels.append({'cx': cx, 'cy': cy, 'txt': txt})

        # Merge labels that are in same column (within 80px X) and close Y (within 40pt)
        used = set()
        merged = []
        raw_labels.sort(key=lambda x: (round(x['cx']/80), x['cy']))
        for i, lb in enumerate(raw_labels):
            if i in used:
                continue
            group = [lb]
            used.add(i)
            for j, lb2 in enumerate(raw_labels):
                if j in used:
                    continue
                if abs(lb2['cx'] - lb['cx']) < 80 and abs(lb2['cy'] - lb['cy']) < 40:
                    group.append(lb2)
                    used.add(j)
            txt = ' '.join(g['txt'] for g in sorted(group, key=lambda x: x['cy']))
            txt = re.sub(r'\s+', ' ', txt).strip()
            cx = sum(g['cx'] for g in group) / len(group)
            cy = sum(g['cy'] for g in group) / len(group)
            merged.append({'cx': cx, 'cy': cy, 'txt': txt})

        # Get images with positions (skip tiny decorative images)
        img_infos = page.get_image_info(xrefs=True)
        img_infos = [i for i in img_infos if i['width'] > 80 and i['height'] > 80]

        for img_info in img_infos:
            bbox = img_info['bbox']
            img_cx = (bbox[0] + bbox[2]) / 2
            img_cy = (bbox[1] + bbox[3]) / 2

            # Find label in same column (closest X), within vertical range of image
            y_lo, y_hi = bbox[1] - 10, bbox[3] + 10
            candidates = [lb for lb in merged if y_lo <= lb['cy'] <= y_hi]
            if not candidates:
                candidates = [lb for lb in merged if abs(lb['cy'] - img_cy) < 120]
            if not candidates:
                continue

            best = min(candidates, key=lambda lb: abs(lb['cx'] - img_cx))
            label = best['txt']
            label = re.sub(r'\s*[-–]\s*', ' – ', label)
            label = re.sub(r'\s+', ' ', label).strip()

            try:
                raw = doc.extract_image(img_info['xref'])
                b64 = img_to_b64jpeg(raw['image'], max_px=400)
            except Exception:
                continue
            entries.append((label, b64))

    doc.close()

    # Deduplicate: keep first image per unique label
    seen = {}
    for name, b64 in entries:
        if name not in seen:
            seen[name] = b64
    entries = list(seen.items())
    print(f'  Unikátních dominant: {len(entries)}')
    for name, _ in entries:
        print(f'    {name}')

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

# Labels read from the rendered PDF pages
MAP_LABELS_P1 = [
    # Row 0 (symbols 1-3)
    'Zpevněná cesta', 'Pěšina', 'Polní a lesní cesta',
    # Row 1 (symbols 4-6) — line/road symbols
    'Trasa vodní dopravy', 'Silnice 1. třídy', 'Ostatní silnice',
    # Row 2 (symbols 7-9)
    'Dálnice', 'Násep', 'Řeka s jezerem',
    # Row 3 (symbols 10-12)
    'Řeka s mostem', 'Řeka s přívozem', 'Pramen',
    # Row 4 (symbols 13-15)
    'Kostel', 'Meteorologická stanice', 'Pomník',
    # Row 5 (symbols 16-18)
    'Pevnost', 'Zřícenina hradu', 'Veřejné tábořiště',
    # Row 6 (symbols 19-21)
    'Autokemping', 'Ohniště, stánek, tůz', 'NTZ (noclehárna, tábořiště, zázemí)',
    # Row 7 (symbols 22-24)
    'Vodní mlýn', 'Rozhledna', 'Orientačně důležitý strom',
]

MAP_LABELS_P2 = [
    # Row 0 (symbols 25-27)
    'Muzeum, galerie', 'Hraniční přechod', 'Hraniční přechod pro pěší a cyklisty',
    # Row 1 (symbols 28-30)
    'Kulturně pozoruhodné místo', 'Ubytovna', 'Hotel',
    # Row 2 (symbols 31-33)
    'Stanice horské služby', 'Restaurace', 'Hranice CHKO',
    # Row 3 (symbols 34-36) — thin line symbols
    'Hranice národního parku', 'Hranice přírodního parku', 'Přírodní zajímavost',
    # Row 4 (symbols 37-39)
    'Sad a zahrada', 'Vinice', 'Porosty křoví',
    # Row 5 (symbols 40-42)
    'Chmelnice', 'Vodojem', 'Pramen (studánka)',
    # Row 6 (symbols 43-45)
    'Veřejné koupaliště', 'Studna', 'Elektrárna',
    # Row 7 (symbols 46-48)
    'Hájovna, myslivna', 'Továrna s komínem', 'Samostatná budova',
]

# Grid crop regions at 2× scale (1191×1684) — (x0, y0, x1, y1) per row
# Columns are the same for both pages: col splits at x≈196 and x≈338
COL_SPLITS_2X = [46, 196, 338, 482]   # left edges of cols + right edge

# Page 1 row splits (y positions of horizontal grid lines at 2× scale)
ROW_SPLITS_P1_2X = [153, 282, 348, 455, 558, 700, 840, 950, 1065]

# Page 2 row splits (two sections with a gap in between)
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
    all_names = all_labels[:]

    for page_idx, row_splits, labels in page_configs:
        page = doc[page_idx]
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)

        sym_idx = 0
        for row in range(len(row_splits) - 1):
            y0 = row_splits[row]
            y1 = row_splits[row + 1]
            for col in range(len(COL_SPLITS_2X) - 1):
                x0 = COL_SPLITS_2X[col]
                x1 = COL_SPLITS_2X[col + 1]
                if sym_idx >= len(labels):
                    break
                cell = img.crop((x0, y0, x1, y1))
                name = labels[sym_idx]
                key = to_key(name)
                b64 = pil_to_b64jpeg(cell, max_px=200, quality=85)
                images[key] = b64
                questions.append({
                    'q': 'Co označuje tato mapová značka?',
                    'img': f'topografie/{key}',
                    'imgClass': 'topo',
                    'a': name,
                    'options': make_options(name, all_names)
                })
                print(f'    [{page_idx+1}] R{row}C{col}: {name}')
                sym_idx += 1

    doc.close()
    write_js('topografie.js', 'topografie', images, questions)

# ─────────────────────────── text questions ──────────────────────────────────

def write_text_questions():
    print('\n📝 Textové otázky')

    uzly = [
        {'q':'Jak se jmenuje uzel tvořící pevnou smyčku, která se neutahuje?','a':'Lodní smyčka (úvazek)','options':['Lodní smyčka (úvazek)','Osmičkový uzel','Tesařský uzel','Dračí smyčka']},
        {'q':'Jaký uzel se používá ke spojování dvou lan stejné tloušťky?','a':'Plochý uzel (čtvercový)','options':['Plochý uzel (čtvercový)','Lodní smyčka','Lodní uzel','Alpský motýl']},
        {'q':'Jak se nazývá uzel ve tvaru číslice 8?','a':'Osmičkový uzel','options':['Osmičkový uzel','Plochý uzel','Tesařský uzel','Prusíkův uzel']},
        {'q':'Jaký uzel se váže na tyč nebo kůl pro upevnění lana?','a':'Tesařský uzel','options':['Tesařský uzel','Lodní smyčka','Plochý uzel','Zkracovák']},
        {'q':'Jak se jmenuje uzel pro zkrácení lana bez stříhání?','a':'Zkracovák','options':['Zkracovák','Alpský motýl','Prusíkův uzel','Dračí smyčka']},
        {'q':'Jaký uzel umožňuje posunování po napnutém laně (třecí uzel)?','a':'Prusíkův uzel','options':['Prusíkův uzel','Zkracovák','Osmičkový uzel','Tesařský uzel']},
        {'q':'Jak se jmenuje uzel pro spojení dvou lan při slaňování?','a':'Osmičkový uzel','options':['Osmičkový uzel','Plochý uzel','Lodní uzel','Prusíkův uzel']},
        {'q':'Jaký uzel zálesáci používají jako základní spojovací uzel?','a':'Plochý uzel (čtvercový)','options':['Plochý uzel (čtvercový)','Osmičkový uzel','Alpský motýl','Lodní smyčka (úvazek)']},
        {'q':'Jak se jmenuje uzel tvořící pevnou smyčku uprostřed lana (pro horolezectví)?','a':'Alpský motýl','options':['Alpský motýl','Lodní smyčka','Osmičkový uzel','Rybářský uzel']},
        {'q':'Jaký uzel tuhne při zatížení a je samosvěrný?','a':'Prusíkův uzel','options':['Prusíkův uzel','Zkracovák','Tesařský uzel','Dračí smyčka']},
        {'q':'Jak se jmenuje uzel pro spojení dvou lan různé tloušťky?','a':'Lodní uzel','options':['Lodní uzel','Plochý uzel','Alpský motýl','Francouzský uzel']},
        {'q':'Jaký uzel tvoří pevnou nesvírající smyčku (záchranářský)?','a':'Lodní smyčka (úvazek)','options':['Lodní smyčka (úvazek)','Stahovací smyčka','Šibeničková klička','Tesařský uzel']},
        {'q':'Jak se nazývá uzel, který se utahuje pod zátěží a slouží k uvázání k předmětu?','a':'Dračí smyčka','options':['Dračí smyčka','Tesařský uzel','Prusíkův uzel','Zkracovák']},
        {'q':'Jaký uzel je vhodný pro napínání šňůry tábora nebo stanu?','a':'Tesařský uzel','options':['Tesařský uzel','Lodní smyčka','Plochý uzel','Alpský motýl']},
    ]

    zdravoveda = [
        {'q':'Jak hluboko stlačujeme hrudník při KPR u dospělého?','a':'5–6 cm','options':['5–6 cm','2–3 cm','8–10 cm','1–2 cm']},
        {'q':'Jaké je správné tempo stlačování hrudníku při KPR?','a':'100–120 stlačení za minutu','options':['100–120 stlačení za minutu','60–80 za minutu','140–160 za minutu','50–60 za minutu']},
        {'q':'Jaký je poměr stlačení ku vdechům při KPR (dospělý, 1 zachránce)?','a':'30 : 2','options':['30 : 2','15 : 2','5 : 1','10 : 2']},
        {'q':'Na jaké číslo voláme záchrannou službu v ČR?','a':'155','options':['155','112','150','158']},
        {'q':'Co uděláme jako první při nálezu bezvědomé osoby (po zajištění bezpečnosti)?','a':'Ověříme reakci a dech','options':['Ověříme reakci a dech','Zahájíme KPR','Zavoláme rodiče','Podáme vodu']},
        {'q':'Jak znehybníme zlomeninu v terénu bez dílen?','a':'Přivážeme k rovné tyči nebo jinému pevnému předmětu','options':['Přivážeme k rovné tyči nebo jinému pevnému předmětu','Pevně zavineme do obvazu','Necháme volně','Přiložíme studený obklad']},
        {'q':'Jak zastavíme silné krvácení z končetiny?','a':'Přímým tlakem na ránu, případně turniketem','options':['Přímým tlakem na ránu, případně turniketem','Zvedneme končetinu nahoru','Přiložíme led','Necháme ránu otevřenou']},
        {'q':'Co uděláme s popáleninou bezprostředně po poranění?','a':'Chladíme tekoucí vodou 10–20 minut','options':['Chladíme tekoucí vodou 10–20 minut','Potřeme máslem','Propíchneme puchýře','Zabalíme do suché tkaniny']},
        {'q':'Jak poznáme přehřátí (úpal)?','a':'Horká suchá kůže, vysoká teplota, zmatenost','options':['Horká suchá kůže, vysoká teplota, zmatenost','Studená vlhká kůže, třesavka','Bolest břicha, nevolnost','Bledost a mdloby']},
        {'q':'Do jaké polohy uložíme dýchající osobu v bezvědomí?','a':'Do stabilizované (zotavovací) polohy','options':['Do stabilizované (zotavovací) polohy','Na záda','Na břicho','Do sedu']},
        {'q':'Jak správně vytáhnout přisáté klíště?','a':'Speciálními kleštěmi co nejblíže kůži, otáčivým pohybem','options':['Speciálními kleštěmi co nejblíže kůži, otáčivým pohybem','Přiložíme zápalku','Potřeme olejem','Překryjeme náplastí a počkáme']},
        {'q':'Co uděláme při podezření na zlomeninu páteře?','a':'Nehýbeme s postiženým, zajistíme odbornou pomoc','options':['Nehýbeme s postiženým, zajistíme odbornou pomoc','Posadíme postiženého','Postiženého otočíme na bok','Postiženého dovedeme do stoje']},
    ]

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

    lines = [
        'var QUESTIONS_DATA=window.QUESTIONS_DATA||(window.QUESTIONS_DATA={});',
        f'QUESTIONS_DATA["uzly"]={json.dumps(uzly, ensure_ascii=False)};',
        f'QUESTIONS_DATA["zdravoveda"]={json.dumps(zdravoveda, ensure_ascii=False)};',
        f'QUESTIONS_DATA["historie"]={json.dumps(historie, ensure_ascii=False)};',
    ]
    path = os.path.join(OUTPUT, 'text_questions.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    kb = os.path.getsize(path) // 1024
    print(f'  ✓ text_questions.js  (uzly:{len(uzly)}, zdravoveda:{len(zdravoveda)}, historie:{len(historie)}, {kb} KB)')

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
