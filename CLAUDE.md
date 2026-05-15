# Zálesák AI Trainer — CLAUDE.md

## Pravidlo pro Claude

**CLAUDE.md je živý dokument.** Po každé změně projektu Claude **musí aktualizovat tento soubor** tak, aby vždy přesně reflektoval aktuální stav projektu.

## Repozitář

https://github.com/knot/zalesak-trainer  
GitHub Pages: **https://knot.github.io/zalesak-trainer/**

## Co je tento projekt

Webová tréninková aplikace pro děti účastnící se Sokolských zálesáckých závodů.

---

## Struktura repozitáře

```
index.html                  # Hlavní aplikace — HTML + CSS + JS (~37 KB)
data/
  questions/
    uzly.json               # Textové otázky: uzly (14)
    zdravoveda.json         # Textové otázky: zdravověda (30)
    historie.json           # Textové otázky: historie Sokola (39)
    prirodniny.json         # Zvířata: 117 druhů s obrázky
    rostliny.json           # Rostliny a houby: 140 druhů s obrázky
    souhvezdi.json          # Souhvězdí: 19 souhvězdí s obrázky
    dominanty.json          # Dominanty ČR: 48 míst s obrázky
    topografie.json         # Mapové značky: 48 značek s obrázky
images/
  prirodniny/               # 117 JPEG souborů
  rostliny/                 # 140 JPEG souborů
  souhvezdi/                # 19 JPEG souborů
  dominanty/                # 48 JPEG souborů
  topografie/               # 48 JPEG souborů
  uzly/                     # 5 JPEG souborů (pouze pro referenci, otázky odstraněny)
scripts/
  extract.py                # Extrakce obrázků z PDF → images/ + data/questions/*.json
  extract_images.py         # Jednorázový skript: base64 → binární soubory (již hotovo)
  extract_questions.py      # Jednorázový skript: JS → JSON (již hotovo)
  fix_dominanty.py          # Jednorázový skript: oprava OCR artefaktů v dominanty.json
  fix_species_names.py      # Jednorázový skript: doplnění druhových jmen
uploads/                    # Zdrojové PDF (lokálně, není v repozitáři — .gitignored)
CLAUDE.md                   # Tento soubor
```

---

## Jak spustit lokálně

```bash
python3 -m http.server 8080 --bind 0.0.0.0
# Otevři: http://localhost:8080
```

## Jak deployovat

```bash
git add index.html data/ images/
git commit -m "popis změny"
git push
# GitHub Pages se aktualizuje automaticky za ~1 minutu
```

---

## Architektura

### index.html
Obsahuje:
- CSS (veškeré styly)
- HTML (8 obrazovek: menu, quiz, výsledek, Morseovka)
- Inline JS: logika kvízu, Morseův modul, načítání dat přes `fetch()`

**Žádná data ani obrázky nejsou v index.html.**

### Načítání dat
`index.html` načítá všechna data asynchronně přes `fetch()` při startu stránky:
```javascript
const MODULES = ['uzly','zdravoveda','historie','prirodniny','rostliny','souhvezdi','dominanty','topografie'];
let QUESTIONS = {};

async function loadQuestions() {
  const results = await Promise.all(
    MODULES.map(m => fetch(`data/questions/${m}.json`).then(r => r.json()))
  );
  MODULES.forEach((m, i) => { QUESTIONS[m] = results[i]; });
}
```

### Obrázky
Obrázky jsou binární JPEG soubory v `images/<kategorie>/<klic>.jpg`.  
Otázky je odkazují přes pole `img`, např. `"img": "prirodniny/bobr"`.  
`index.html` zobrazuje obrázek jako: `imgEl.src = 'images/' + q.img + '.jpg'`

### Formát otázky (JSON)
```json
{ "q": "Co je toto zvíře?", "img": "prirodniny/bobr_evropsky", "a": "bobr evropský", "options": ["plch velký", "liška obecná", "bobr evropský", "netopýr velký"] }
```
Pro topografii navíc: `"imgClass": "topo"` (zobrazí menší obrázek).

### Kategorie

| Kategorie | Typ | Počet | Soubor |
|-----------|-----|-------|--------|
| `uzly` | text | 14 | questions/uzly.json |
| `zdravoveda` | text | 30 | questions/zdravoveda.json |
| `historie` | text | 39 | questions/historie.json |
| `prirodniny` | obrázek | 117 | questions/prirodniny.json |
| `rostliny` | obrázek | 140 | questions/rostliny.json |
| `souhvezdi` | obrázek | 19 | questions/souhvezdi.json |
| `dominanty` | obrázek | 48 | questions/dominanty.json |
| `topografie` | obrázek | 48 | questions/topografie.json |

Kvíz vybere **20 náhodných otázek** ze zvolené kategorie (nebo mix všech).

### Morseův modul
Samostatná obrazovka se třemi režimy:
- **📖 Abeceda** — přehled + zvukové přehrávání (Web Audio API)
- **👁️ Přijímat** — slyšíš/vidíš signál, hádáš písmeno/slovo
- **✍️ Vysílat** — dostaneš slovo, zadáváš tečky/čárky

---

## Jak přidat nebo aktualizovat data

### Přidat textovou otázku
V příslušném `data/questions/<modul>.json` přidej do pole:
```json
{ "q": "Otázka?", "a": "Správná odpověď", "options": ["A", "B", "C", "D"] }
```

### Přidat obrázkovou otázku
1. Přidej JPEG do `images/<kategorie>/<klic>.jpg`
2. Přidej záznam do `data/questions/<kategorie>.json`:
```json
{ "q": "Co je toto zvíře?", "img": "prirodniny/<klic>", "a": "název druhu", "options": [...] }
```

### Aktualizovat data z PDF
1. Vlož nová PDF do adresáře `uploads/`
2. Spusť `python3 scripts/extract.py`
3. Skript přepíše soubory v `data/questions/` a `images/`

---

## Zdrojové PDF (lokálně v uploads/)

- `Přírodniny - zvířata.pdf` — zvířata (savci, ptáci, plazi, ryby, bezobratlí)
- `rostliny - žactvo.pdf` — rostliny a houby
- `Souhvězdí žactvo.pdf` — souhvězdí
- `mistopis.pdf` — dominanty ČR (hrady, zámky, hory, technické památky)
- `Mapové značky 2019.pdf` — turistické mapové značky
- `Historie a současnost sokola.pdf` — otázky z historie Sokola

Obrázky jsou extrahovány pomocí PyMuPDF + PIL a ukládány jako binární JPEG.
