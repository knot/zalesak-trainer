#!/usr/bin/env python3
"""Add missing species qualifier to single-word animal/plant names."""

import json, os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'questions')

RENAMES = {
    # ── Savci ──────────────────────────────────────────────────────────────
    "bobr":              "bobr evropský",
    "jelen":             "jelen lesní",
    "jezevec":           "jezevec lesní",
    "ježek":             "ježek evropský",
    "kamzík":            "kamzík horský",
    "králík":            "králík divoký",
    "krtek":             "krtek obecný",
    "křeček":            "křeček polní",
    "medvěd":            "medvěd hnědý",
    "muflon":            "muflon evropský",
    "myš":               "myš lesní",
    "netopýr":           "netopýr velký",
    "nutrie":            "nutrie bahenní",
    "nutrie vs. ondatra":"nutrie bahenní vs. ondatra pižmová",
    "ondatra":           "ondatra pižmová",
    "plch":              "plch velký",
    "potkan":            "potkan obecný",
    "rejsek":            "rejsek obecný",
    "vlk":               "vlk obecný",
    "vydra":             "vydra říční",
    "zajíc":             "zajíc polní",
    # ── Ryby ───────────────────────────────────────────────────────────────
    "candát":            "candát obecný",
    "cejn":              "cejn velký",
    "karas":             "karas obecný",
    "lín":               "lín obecný",
    "okoun":             "okoun říční",
    "pstruh":            "pstruh obecný",
    "úhoř":              "úhoř říční",
    # ── Ptáci ──────────────────────────────────────────────────────────────
    "brhlík":            "brhlík lesní",
    "červenka":          "červenka obecná",
    "havran":            "havran polní",
    "holub":             "holub domácí",
    "hrdlička":          "hrdlička zahradní",
    "husa":              "husa velká",
    "kachna":            "kachna divoká",
    "káně":              "káně lesní",
    "kormorán":          "kormorán velký",
    "kukačka":           "kukačka obecná",
    "ledňáček":          "ledňáček říční",
    "pěnkava":           "pěnkava obecná",
    "poštolka":          "poštolka obecná",
    "racek":             "racek chechtavý",
    "stehlík":           "stehlík obecný",
    "straka":            "straka obecná",
    "strakapoud":        "strakapoud velký",
    "sýček":             "sýček obecný",
    "špaček":            "špaček obecný",
    "vlaštovka":         "vlaštovka obecná",
    "volavka":           "volavka popelavá",
    "vrabec":            "vrabec domácí",
    "výr":               "výr velký",
    "zvonek":            "zvonek zelený",
    # ── Plazi a obojživelníci ───────────────────────────────────────────────
    "mlok":              "mlok skvrnitý",
    "slepýš":            "slepýš křehký",
    # ── Bezobratlí ─────────────────────────────────────────────────────────
    "bělásek":           "bělásek zelný",
    "chrobák":           "chrobák obecný",
    "chrostík":          "chrostík velký",
    "chroust":           "chroust obecný",
    "hlemýžď":           "hlemýžď zahradní",
    "mnohonožka":        "mnohonožka plochá",
    "motýlice":          "motýlice obecná",
    "pestřenka":         "pestřenka pruhovaná",
    "pijavka":           "pijavka lékařská",
    "plzák":             "plzák španělský",
    "ruměnice":          "ruměnice pospolná",
    "saranče":           "saranče stěhovavá",
    "sekáč":             "sekáč rohatý",
    "sršeň":             "sršeň obecný",
    "stonožka":          "stonožka obecná",
    "střevlík":          "střevlík zahradní",
    "světluška":         "světluška obecná",
    "sýkora":            "sýkora koňadra",
    "šídlo":             "šídlo modré",
    "škeble":            "škeble rybničná",
    "škvor":             "škvor obecný",
    "čmelák":            "čmelák zemní",
    # ── Rostliny ───────────────────────────────────────────────────────────
    "hloh":              "hloh obecný",
    "leknín":            "leknín bílý",
    # ── Houby ──────────────────────────────────────────────────────────────
    "kotrč":             "kotrč kadeřavý",
}

def fix_file(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    changed = 0
    for q in data:
        old_a = q['a']
        q['a'] = RENAMES.get(q['a'], q['a'])
        if q['a'] != old_a:
            changed += 1

        new_opts = []
        for o in q['options']:
            new_o = RENAMES.get(o, o)
            if new_o != o:
                changed += 1
            new_opts.append(new_o)
        q['options'] = new_opts

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'{filename}: {changed} names updated')

fix_file('prirodniny.json')
fix_file('rostliny.json')
print('Done.')
