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
index.html              # Hlavní aplikace — shell bez vložených obrázků (~37 KB)
data/
  text_questions.js     # Textové otázky: uzly (14), zdravověda (12), historie (39)
  prirodniny.js         # Zvířata: 97 druhů s obrázky
  rostliny.js           # Rostliny a houby: 100 druhů s obrázky
  souhvezdi.js          # Souhvězdí: 14 souhvězdí s obrázky
  dominanty.js          # Dominanty ČR: 52 míst s obrázky (z mistopis.pdf)
  topografie.js         # Mapové značky: 48 značek s obrázky
scripts/
  extract.py            # Jednorázový skript pro extrakci obrázků z PDF
uploads/                # Zdrojové PDF (lokálně, není v repozitáři — .gitignored)
CLAUDE.md               # Tento soubor
```

---

## Jak spustit lokálně

```bash
python3 -m http.server 8080 --bind 0.0.0.0
# Otevři: http://localhost:8080
```

## Jak deployovat

```bash
git add index.html data/
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
- `<script src="data/...">` tagy (nacházejí se před inline skriptem)
- Logika kvízu a Morseův modul (inline JS)

**Žádné obrázky nejsou v index.html** — jsou v souborech `data/*.js`.

### Datové soubory (`data/*.js`)
Každý soubor nastavuje globální proměnné:
```javascript
window.IMAGES_DATA["kategorie"] = { "klic": "data:image/jpeg;base64,...", ... };
window.QUESTIONS_DATA["kategorie"] = [ { q, img, a, options }, ... ];
```

Inline skript v index.html pak přistupuje k nim přes:
```javascript
const IMAGES    = window.IMAGES_DATA    || {};
const QUESTIONS = window.QUESTIONS_DATA || {};
```

### Kategorie

| Kategorie | Typ | Počet | Soubor |
|-----------|-----|-------|--------|
| `uzly` | text | 14 | text_questions.js |
| `zdravoveda` | text | 12 | text_questions.js |
| `historie` | text | 39 | text_questions.js |
| `prirodniny` | obrázek | 97 | prirodniny.js |
| `rostliny` | obrázek | 100 | rostliny.js |
| `souhvezdi` | obrázek | 14 | souhvezdi.js |
| `dominanty` | obrázek | 52 | dominanty.js |
| `topografie` | obrázek | 48 | topografie.js |

Kvíz vybere **20 náhodných otázek** ze zvolené kategorie (nebo mix všech).

### Morseův modul
Samostatná obrazovka se třemi režimy:
- **📖 Abeceda** — přehled + zvukové přehrávání (Web Audio API)
- **👁️ Přijímat** — slyšíš/vidíš signál, hádáš písmeno/slovo
- **✍️ Vysílat** — dostaneš slovo, zadáváš tečky/čárky

---

## Jak přidat nebo aktualizovat data

### Přidat textovou otázku
V `data/text_questions.js` najdi příslušné pole (`QUESTIONS_DATA["uzly"]` atd.) a přidej:
```javascript
{ q: "Otázka?", a: "Správná odpověď", options: ["A","B","C","D"] },
```

### Aktualizovat obrázková data z PDF
1. Vlož nová PDF do adresáře `uploads/`
2. Spusť `python3 scripts/extract.py`
3. Skript přepíše soubory v `data/`

### Formát otázky s obrázkem
```javascript
{ q: "Co je toto zvíře?", img: "prirodniny/klic_obrazku", a: "Správná odpověď", options: [...] }
// Pro topografii navíc: imgClass: "topo"  (zobrazí menší obrázek)
```

---

## Zdrojové PDF (lokálně v uploads/)

- `Přírodniny - zvířata.pdf` — 97 zvířat (savci, ptáci, plazi, ryby, bezobratlí)
- `rostliny - žactvo.pdf` — 100 rostlin a hub
- `Souhvězdí žactvo.pdf` — 14 souhvězdí
- `mistopis.pdf` — ~52 dominant ČR (hrady, zámky, hory, technické památky)
- `Mapové značky 2019.pdf` — 48 turistických mapových značek
- `Historie a současnost sokola.pdf` — 39 otázek z historie Sokola

Obrázky jsou extrahovány pomocí PyMuPDF + PIL a embedovány jako base64 JPEG v JS souborech.
