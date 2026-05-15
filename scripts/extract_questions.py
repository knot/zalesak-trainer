#!/usr/bin/env python3
"""Extract QUESTIONS_DATA from data/*.js files to data/questions/<module>.json."""

import os
import re
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR  = os.path.join(DATA_DIR, 'questions')

os.makedirs(OUT_DIR, exist_ok=True)

# Modules and their source files
SOURCES = {
    'text_questions.js': ['uzly', 'zdravoveda', 'historie'],
    'prirodniny.js':     ['prirodniny'],
    'rostliny.js':       ['rostliny'],
    'souhvezdi.js':      ['souhvezdi'],
    'dominanty.js':      ['dominanty'],
    'topografie.js':     ['topografie'],
    'uzly.js':           [],  # now empty
}

for filename, cats in SOURCES.items():
    if not cats:
        continue
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    for cat in cats:
        # Find the questions array: either direct assignment or .concat() pattern
        pat = (
            r'QUESTIONS_DATA\["' + re.escape(cat) + r'"\]'
            r'(?:=|\s*=\s*\(QUESTIONS_DATA\["' + re.escape(cat) + r'"\]\|\|\[\]\)\.concat)\s*\(?\s*(\[)'
        )
        m = re.search(pat, content)
        if not m:
            # Fallback: find the last '[' in any assignment for this cat
            m = re.search(r'QUESTIONS_DATA\["' + re.escape(cat) + r'"\][^[]*\.concat\(\s*(\[)', content)
        if not m:
            m = re.search(r'QUESTIONS_DATA\["' + re.escape(cat) + r'"\]\s*=\s*(\[)', content)
        if not m:
            print(f'  WARNING: {cat} not found in {filename}')
            continue

        # Walk from the opening '[' to its matching ']', respecting strings
        start = m.start(1)
        depth, in_string, escape = 0, False, False
        for i, ch in enumerate(content[start:], start):
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    raw = content[start:i+1]
                    # Strip trailing commas before ] or } (JS allows, JSON doesn't)
                    raw = re.sub(r',\s*([}\]])', r'\1', raw)
                    questions = json.loads(raw)
                    break
        else:
            print(f'  WARNING: could not find closing ] for {cat}')
            continue
        out_path = os.path.join(OUT_DIR, f'{cat}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f'  {cat}: {len(questions)} questions → data/questions/{cat}.json')

print('Done.')
