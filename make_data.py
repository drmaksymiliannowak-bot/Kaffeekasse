#!/usr/bin/env python3
"""Erzeugt data.json (öffentlich) aus dem Kaffeekasse-HTML-Backup.

Aufruf:  python3 make_data.py "Kaffeekasse 3.html"

Es werden Mitglieder, Monate, der Bezahl-Link und eine Summen-Übersicht
(Kassenstand, Einnahmen, Ausgaben je Kategorie/Monat) übernommen.
Einzelne Ausgabenposten und Stichwörter bleiben privat.
"""
import json
import re
import sys

if len(sys.argv) != 2:
    sys.exit('Aufruf: python3 make_data.py <Backup.html>')

html = open(sys.argv[1], encoding='utf-8').read()
m = re.search(r'<script id="embedded-kaffeekasse-data"[^>]*>([\s\S]*?)</script>', html)
if not m:
    sys.exit('Keine eingebetteten Kaffeekasse-Daten gefunden.')
state = json.loads(m.group(1))

def active(member, ym):
    if member.get('startMonth') and ym < member['startMonth']:
        return False
    if member.get('endMonth') and ym > member['endMonth']:
        return False
    return True


# Einnahmen: wie im Tool alle bezahlten Monate aktiver Mitglieder (inkl. Spenden-Posten)
by_month = {}
income = 0.0
for x in state['members']:
    for ym, e in (x.get('months') or {}).items():
        if e and e.get('status') == 'paid' and active(x, ym):
            amt = float(e.get('amount') or x['rate'])
            income += amt
            by_month.setdefault(ym, {'income': 0.0, 'expenses': 0.0})['income'] += amt

expenses = 0.0
by_category = {}
for e in state.get('expenses', []):
    amt = float(e.get('amount') or 0)
    expenses += amt
    by_category[e['category']] = by_category.get(e['category'], 0.0) + amt
    ym = e['date'][:7]
    by_month.setdefault(ym, {'income': 0.0, 'expenses': 0.0})['expenses'] += amt

start = float(state.get('revolutInitialBalance') or 0)
auto_balance = start + income - expenses
balance = float(state.get('manualKaffeekasseAmount') or 0) if state.get('useManualKaffeekasse') else auto_balance

summary = {
    'startBalance': round(start, 2),
    'income': round(income, 2),
    'expenses': round(expenses, 2),
    'balance': round(balance, 2),
    'byCategory': [
        {'category': c, 'amount': round(a, 2)}
        for c, a in sorted(by_category.items(), key=lambda kv: -kv[1])
    ],
    'byMonth': {
        k: {'income': round(v['income'], 2), 'expenses': round(v['expenses'], 2)}
        for k, v in sorted(by_month.items())
    },
}

public = {
    'paymentLink': state.get('paymentLink', ''),
    'summary': summary,
    'members': [
        {
            'id': x['id'],
            'name': x['name'],
            'rate': x['rate'],
            'startMonth': x.get('startMonth', ''),
            'endMonth': x.get('endMonth', ''),
            'months': x.get('months', {}),
        }
        for x in state['members']
        if x['name'].strip().upper() != 'KAFFEKASSE'  # interner Sammelposten
    ],
}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(public, f, ensure_ascii=False, indent=1)
print(f"data.json geschrieben: {len(public['members'])} Mitglieder")
