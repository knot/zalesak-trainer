#!/usr/bin/env python3
"""Fix OCR-mangled names and simplify labels in dominanty.json."""

import json, os

PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'questions', 'dominanty.json')

# old (broken) → new (correct, simplified)
NAME_MAP = {
    "Bouzo v – hrad":                                                   "Bouzov",
    "Brno – Špilberk":                                                  "Brno – Špilberk",
    "Brno – vila Tugendhat":                                            "Vila Tugendhat",
    "Buchlo v – hrad":                                                  "Buchlov",
    "České Budějovice – náměstí s černo u věží":                       "České Budějovice – Černá věž",
    "Děčínský Sněžní k – hora s rozhledno u":                          "Děčínský Sněžník",
    "Dlouhé stráně – horní vodní nádrž":                               "Dlouhé stráně",
    "Domažlice – náměstí s válcovo u šikmo u věží":                    "Domažlice – šikmá věž",
    "Hluboká nad Vltavo u – zámek":                                    "Hluboká nad Vltavou",
    "Cheb – Špalíček (architek tura)":                                  "Cheb – Špalíček",
    "Kačina – Zámek":                                                   "Kačina",
    "Karlštejn – hrad":                                                 "Karlštejn",
    "Kašperk – zříceni na hradu":                                       "Kašperk",
    "Konopiště – zámek":                                                "Konopiště",
    "Kost – hrad":                                                      "Kost",
    "Křivoklát":                                                        "Křivoklát",
    "Kuks – Hospital":                                                  "Kuks",
    "Kunětická Hora – hrad":                                            "Kunětická hora",
    "Kutná Hora – chrám sv. Barbory":                                   "Kutná Hora – chrám sv. Barbory",
    "Lány – zámek":                                                     "Lány",
    "Lednicko – valtický areál – minaret, Tři grácie, zámek Lednice s kaplí": "Lednicko-valtický areál",
    "Litomyšl – zámek":                                                 "Litomyšl",
    "Macocha – propast":                                                "Macocha",
    "Olomouc – radnice s orlojem":                                      "Olomouc – radnice s orlojem",
    "Ostrava – Vítkovické pece":                                        "Vítkovické pece",
    "Panská skála u Kamenickéh o Šenova – skalní útvar":               "Panská skála",
    "Písek – kamenný most":                                             "Písek – kamenný most",
    "Plumlo v – zámek":                                                 "Plumlov",
    "Plzeň – chrám sv. Bartolomě je":                                   "Plzeň – chrám sv. Bartoloměje",
    "Plzeň – Velká synagog a":                                          "Plzeň – Velká synagoga",
    "Prachovské skály – skalní útvary":                                 "Prachovské skály",
    "Praděd – hora, vysílač":                                           "Praděd",
    "Praha – chrám sv. Víta":                                           "Chrám sv. Víta",
    "Praha – Karlů v most":                                             "Karlův most",
    "Praha – Národní divadlo":                                          "Národní divadlo",
    "Praha – Petřínská rozhled na":                                     "Petřínská rozhledna",
    "Praha – Tyršůvdům":                                                "Tyršův dům",
    "Praha – Vyšehrad":                                                 "Vyšehrad",
    "Pravčická brá na – skalní útvar":                                  "Pravčická brána",
    "Rožno v pod Radhoštěm – skanzen":                                  "Rožnov pod Radhoštěm",
    "Sněžka – hora":                                                    "Sněžka",
    "Sv. Hostýn – poutní kostel":                                       "Sv. Hostýn",
    "Šviho v – vodní hrad":                                             "Švihov",
    "Telč – náměstí se zámkem":                                         "Telč",
    "Třebíč – bazilik a":                                               "Třebíč – bazilika",
    "Velký Blaní k – rozhled na":                                       "Velký Blaník",
    "Žďár nad Sázavo u – poutní areál Zelená hora":                     "Zelená hora",
    "Zvíko v – hrad":                                                   "Zvíkov",
}

with open(PATH, encoding='utf-8') as f:
    data = json.load(f)

for q in data:
    q['a'] = NAME_MAP.get(q['a'], q['a'])
    q['options'] = [NAME_MAP.get(o, o) for o in q['options']]

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Fixed {len(data)} questions.')
