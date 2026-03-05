#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
צפי מכר שבועי לפסח — מחולק למלאי כשל"פ ומלאי רגיל
Generates: passover_forecast.html (shareable with colleagues)
"""

import sys
import json
import math
from datetime import date, timedelta

# ── paths ────────────────────────────────────────────────────────────────────
import os as _os
sys.path.insert(0, str(_os.path.dirname(_os.path.abspath(__file__))))

PALLET   = 2400
PRODUCTS = ['chocolate', 'vanilla', 'mango', 'pistachio']
PROD_HEB = {'chocolate': 'שוקולד', 'vanilla': 'וניל', 'mango': 'מנגו', 'pistachio': 'פיסטוק'}

# KFP production pallets per product (mango = 0)
KFP_PALLETS = {'chocolate': 6, 'vanilla': 6, 'mango': 0, 'pistachio': 6}

# Date constants
KFP_WIN_S  = date(2026, 3, 9)
KFP_WIN_E  = date(2026, 3, 26)
PROD_START = date(2026, 3, 8)
FEB_DAYS   = 26

# ── data load ─────────────────────────────────────────────────────────────────
try:
    from parsers import consolidate_data  # type: ignore
    _d   = consolidate_data()
    _feb = _d['monthly_data']['February 2026']['combined']
    feb_units = {p: _feb[p]['units'] for p in PRODUCTS}
    _wh  = _d['warehouse'].get('products', {})
    _di  = _d['dist_inv']
    reg_stock_units = {
        p: (_wh.get(p, {}).get('units', 0)
            + _di.get('icedream', {}).get('products', {}).get(p, {}).get('units', 0)
            + _di.get('mayyan',   {}).get('products', {}).get(p, {}).get('units', 0))
        for p in PRODUCTS
    }
    # Per-distributor February sales
    feb_by_dist = {
        'mayyan':   {p: _feb[p]['mayyan_units']    for p in PRODUCTS},
        'icedream': {p: _feb[p]['icedreams_units'] for p in PRODUCTS},
    }
    print("✓ Live data loaded from parsers")
except Exception as exc:
    print(f"⚠️  Using sample data ({exc})")
    feb_units = {'chocolate': 11223, 'vanilla': 11292, 'mango': 6771, 'pistachio': 10250}
    reg_stock_units = {'chocolate': 22140, 'vanilla': 32454, 'mango': 34436, 'pistachio': 3227}
    feb_by_dist = {
        'mayyan':   {'chocolate': 9707, 'vanilla': 10020, 'mango': 6085, 'pistachio': 7650},
        'icedream': {'chocolate': 1516, 'vanilla': 1272,  'mango': 686,  'pistachio': 2600},
    }

# ── daily rates ───────────────────────────────────────────────────────────────
reg_daily_u  = {p: feb_units[p] / FEB_DAYS for p in PRODUCTS}  # units/day
# KFP: total production spread evenly over 18-day window
kfp_daily_u  = {p: KFP_PALLETS[p] * PALLET / 18 for p in PRODUCTS}

# ── KFP production schedule (4 pallets/day capacity) ─────────────────────────
# Order: pistachio → chocolate → vanilla (heaviest first)
_rem  = dict(KFP_PALLETS)
_d_ptr = PROD_START
prod_sched = {}   # date → {product: pallets}
for _prod in ['pistachio', 'chocolate', 'vanilla', 'mango']:
    while _rem[_prod] > 0:
        if _d_ptr.weekday() == 5:          # skip Saturday
            _d_ptr += timedelta(days=1)
            continue
        _cap_used = sum(prod_sched.get(_d_ptr, {}).values())
        _cap_free = 4 - _cap_used
        if _cap_free <= 0:
            _d_ptr += timedelta(days=1)
            continue
        _amt = min(_rem[_prod], _cap_free)
        prod_sched.setdefault(_d_ptr, {})[_prod] = _amt
        _rem[_prod] -= _amt

# ── weeks ─────────────────────────────────────────────────────────────────────
WEEKS = [
    ("שבוע 1\n01/03–07/03", date(2026, 3,  1), date(2026, 3,  7)),
    ("שבוע 2\n08/03–14/03", date(2026, 3,  8), date(2026, 3, 14)),
    ("שבוע 3\n15/03–21/03", date(2026, 3, 15), date(2026, 3, 21)),
    ("שבוע 4\n22/03–28/03", date(2026, 3, 22), date(2026, 3, 28)),
    ("שבוע 5\n29/03–04/04", date(2026, 3, 29), date(2026, 4,  4)),
    ("שבוע 6\n05/04–09/04", date(2026, 4,  5), date(2026, 4,  9)),
]

# ── day-by-day simulation ─────────────────────────────────────────────────────
reg_bal = {p: float(reg_stock_units[p]) for p in PRODUCTS}
kfp_bal = {p: 0.0 for p in PRODUCTS}

weekly = []
for w_label, w_start, w_end in WEEKS:
    w = {
        'label': w_label,
        'label_short': w_label.split('\n')[1],
        'reg_sold': {p: 0.0 for p in PRODUCTS},
        'kfp_sold': {p: 0.0 for p in PRODUCTS},
        'in_kfp_window': KFP_WIN_S <= w_start <= KFP_WIN_E or KFP_WIN_S <= w_end <= KFP_WIN_E
                          or (w_start <= KFP_WIN_S and w_end >= KFP_WIN_E),
    }
    d = w_start
    while d <= w_end:
        # production adds to KFP inventory
        for p, pallets in prod_sched.get(d, {}).items():
            kfp_bal[p] += pallets * PALLET

        in_kfp = KFP_WIN_S <= d <= KFP_WIN_E
        for p in PRODUCTS:
            # KFP sales during window (capped by balance)
            if in_kfp and kfp_bal[p] > 0:
                sell = min(kfp_daily_u[p], kfp_bal[p])
                kfp_bal[p] -= sell
                w['kfp_sold'][p] += sell
            # Regular sales every day (capped by balance)
            sell_r = min(reg_daily_u[p], reg_bal[p])
            reg_bal[p] -= sell_r
            w['reg_sold'][p] += sell_r
        d += timedelta(days=1)

    # convert to pallets
    w['reg_sold_p']  = {p: round(w['reg_sold'][p] / PALLET, 2) for p in PRODUCTS}
    w['kfp_sold_p']  = {p: round(w['kfp_sold'][p] / PALLET, 2) for p in PRODUCTS}
    w['reg_bal_p']   = {p: round(reg_bal[p] / PALLET, 1)       for p in PRODUCTS}
    w['kfp_bal_p']   = {p: round(kfp_bal[p] / PALLET, 1)       for p in PRODUCTS}
    w['total_sold_p']= sum(w['reg_sold_p'].values()) + sum(w['kfp_sold_p'].values())
    weekly.append(w)

# ── per-distributor KFP allocation & weekly pull schedule ────────────────────
KFP_PRODUCTS   = ['chocolate', 'vanilla', 'pistachio']
GROWTH_KFP     = {'chocolate': 1.5, 'vanilla': 1.5, 'pistachio': 1.6}
DIST_KEYS      = ['mayyan', 'icedream']
DIST_HEB       = {'mayyan': 'מעיין נציגויות', 'icedream': 'אייסדרים'}
DIST_COL_MAIN  = {'mayyan': '#0f3460',  'icedream': '#e94560'}
DIST_COL_LIGHT = {'mayyan': '#d0d9ef', 'icedream': '#f9d0d8'}

# Step 1: raw demand per distributor per KFP product (units)
_dist_raw = {}
for dk in DIST_KEYS:
    _dist_raw[dk] = {}
    for p in KFP_PRODUCTS:
        daily = feb_by_dist[dk].get(p, 0) / FEB_DAYS
        _dist_raw[dk][p] = daily * 18 * GROWTH_KFP[p]   # units over 18-day window

# Step 2: proportional allocation → whole pallets summing to KFP_PALLETS[p]
dist_kfp_p = {dk: {} for dk in DIST_KEYS}
for p in KFP_PRODUCTS:
    total_raw = sum(_dist_raw[dk][p] for dk in DIST_KEYS)
    alloc = {}
    for dk in DIST_KEYS:
        alloc[dk] = round(KFP_PALLETS[p] * _dist_raw[dk][p] / total_raw) if total_raw > 0 else 0
    # Fix rounding drift
    diff = KFP_PALLETS[p] - sum(alloc.values())
    if diff != 0:
        # Give remainder to the distributor with largest raw share
        biggest = max(DIST_KEYS, key=lambda dk: _dist_raw[dk][p])
        alloc[biggest] += diff
    for dk in DIST_KEYS:
        dist_kfp_p[dk][p] = alloc[dk]

# Step 3: spread each distributor's total over the 3 KFP weeks proportionally
#   KFP window: 9/3–26/3 = 18 days
#   W2 (8/3–14/3): KFP selling days 9–14 Mar = 6
#   W3 (15/3–21/3): 7 days
#   W4 (22/3–28/3): 22–26 Mar = 5 days (window closes 26/3)
KFP_WEEK_LABELS  = ['08/03–14/03', '15/03–21/03', '22/03–26/03']
KFP_WEEK_DAYS    = [6, 7, 5]   # KFP selling days per week
KFP_WIN_TOTAL    = 18

dist_weekly_p = {}   # dist_weekly_p[dk][p] = [w2, w3, w4]  (pallets, 1 decimal)
for dk in DIST_KEYS:
    dist_weekly_p[dk] = {}
    for p in KFP_PRODUCTS:
        total_p = dist_kfp_p[dk][p]
        dist_weekly_p[dk][p] = [
            round(total_p * d / KFP_WIN_TOTAL, 1) for d in KFP_WEEK_DAYS
        ]

# Step 4: build Chart.js datasets for the distributor pull chart
# Grouped stacked bars: X = 3 KFP weeks, groups = 2 distributors, stack = products
dist_chart_labels_js = json.dumps(KFP_WEEK_LABELS)
dist_datasets = []
prod_col = {'chocolate': '#7B4B2A', 'vanilla': '#C49A3C', 'pistachio': '#4A7C3F'}
prod_col_light = {'chocolate': '#C08060', 'vanilla': '#E8CB70', 'pistachio': '#80B870'}

for p in KFP_PRODUCTS:
    for dk in DIST_KEYS:
        vals = dist_weekly_p[dk][p]
        base_col = prod_col[p] if dk == 'mayyan' else prod_col_light[p]
        dist_datasets.append({
            'label':           f"{DIST_HEB[dk]} — {PROD_HEB[p]}",
            'data':            vals,
            'backgroundColor': base_col,
            'stack':           dk,
            'borderWidth':     1,
            'borderColor':     '#fff',
        })

# Build HTML table for the distributor section
def _dist_table():
    hdr  = '<tr><th>מפיץ</th><th>מוצר</th>'
    hdr += ''.join(f'<th>{w}</th>' for w in KFP_WEEK_LABELS)
    hdr += '<th>סה"כ</th></tr>'
    rows = ''
    for dk in DIST_KEYS:
        dist_total_by_week = [0.0, 0.0, 0.0]
        dist_grand = 0
        for p in KFP_PRODUCTS:
            vals = dist_weekly_p[dk][p]
            total_p = dist_kfp_p[dk][p]
            dist_grand += total_p
            for i, v in enumerate(vals):
                dist_total_by_week[i] += v
            cells = ''.join(f'<td>{v:.1f}</td>' for v in vals)
            rows += (f'<tr><td class="dist-name">{DIST_HEB[dk]}</td>'
                     f'<td>{PROD_HEB[p]}</td>{cells}<td class="total-col">{total_p}</td></tr>')
        # distributor subtotal
        sub_cells = ''.join(f'<td class="subtotal">{v:.1f}</td>' for v in dist_total_by_week)
        rows += (f'<tr class="subtotal-row"><td colspan="2">סה"כ {DIST_HEB[dk]}</td>'
                 f'{sub_cells}<td class="subtotal total-col">{dist_grand}</td></tr>')
    # grand total row
    gt_by_week = [sum(dist_weekly_p[dk][p][i] for dk in DIST_KEYS for p in KFP_PRODUCTS)
                  for i in range(3)]
    gt_total = sum(KFP_PALLETS[p] for p in KFP_PRODUCTS)
    gt_cells = ''.join(f'<td class="grand-total">{v:.1f}</td>' for v in gt_by_week)
    rows += (f'<tr class="grand-row"><td colspan="2">🔢 סה"כ כולל</td>'
             f'{gt_cells}<td class="grand-total total-col">{gt_total}</td></tr>')
    return f'<table class="dist-table"><thead>{hdr}</thead><tbody>{rows}</tbody></table>'

dist_table_html = _dist_table()

# ── summary stats ─────────────────────────────────────────────────────────────
total_kfp_prod  = sum(KFP_PALLETS.values())  # 18
total_reg_avail = sum(reg_stock_units.values()) / PALLET
total_kfp_sold  = sum(sum(w['kfp_sold_p'].values()) for w in weekly)
total_reg_sold  = sum(sum(w['reg_sold_p'].values()) for w in weekly)
kfp_remaining   = sum(kfp_bal.values()) / PALLET
reg_remaining   = sum(reg_bal.values()) / PALLET

# ── JSON for charts ───────────────────────────────────────────────────────────
labels_js = json.dumps([w['label_short'] for w in weekly])

# Colors
COL_REG = {'chocolate': '#7B4B2A', 'vanilla': '#C49A3C', 'mango': '#D4660A', 'pistachio': '#4A7C3F'}
COL_KFP = {'chocolate': '#E8956D', 'vanilla': '#F5D060', 'mango': '#F5A623', 'pistachio': '#8DCE6E'}

# Build datasets for Chart.js (stacked bar)
# 4 regular datasets + 3 KFP datasets (no mango KFP)
def mk_dataset(product, is_kfp, stack_group):
    vals = [w['kfp_sold_p'][product] if is_kfp else w['reg_sold_p'][product] for w in weekly]
    _type_lbl = 'כשל"פ' if is_kfp else 'רגיל'
    label = f"{_type_lbl} {PROD_HEB[product]}"
    color = COL_KFP[product] if is_kfp else COL_REG[product]
    return {
        'label': label,
        'data': vals,
        'backgroundColor': color,
        'stack': stack_group,
        'borderWidth': 1,
        'borderColor': '#fff',
    }

sales_datasets = []
# KFP stack (right bar of each group): chocolate, vanilla, pistachio
for p in ['chocolate', 'vanilla', 'pistachio']:
    sales_datasets.append(mk_dataset(p, True,  'kfp'))
# Regular stack (left bar of each group)
for p in ['chocolate', 'vanilla', 'mango', 'pistachio']:
    sales_datasets.append(mk_dataset(p, False, 'regular'))

# Balance line data (end-of-week)
bal_datasets = []
for p in PRODUCTS:
    reg_series = [w['reg_bal_p'][p] for w in weekly]
    kfp_series = [w['kfp_bal_p'][p] for w in weekly]
    bal_datasets.append({
        'label': f"מלאי רגיל — {PROD_HEB[p]}",
        'data': reg_series,
        'borderColor': COL_REG[p],
        'backgroundColor': COL_REG[p] + '22',
        'tension': 0.3,
        'borderDash': [],
        'fill': False,
    })
    if KFP_PALLETS[p] > 0:
        bal_datasets.append({
            'label': f"מלאי כשל\"פ — {PROD_HEB[p]}",
            'data': kfp_series,
            'borderColor': COL_KFP[p],
            'backgroundColor': COL_KFP[p] + '22',
            'tension': 0.3,
            'borderDash': [6, 3],
            'fill': False,
        })

# Weekly total line
total_series = [round(w['total_sold_p'], 1) for w in weekly]

# ── build production timeline data ────────────────────────────────────────────
prod_events = []
for d, prods in sorted(prod_sched.items()):
    for p, pal in prods.items():
        prod_events.append(f"{d.strftime('%d/%m')} — {PROD_HEB[p]} {pal} מש׳")

# ── HTML ─────────────────────────────────────────────────────────────────────
table_rows = ""
for p in PRODUCTS:
    is_kfp = KFP_PALLETS[p] > 0
    kfp_badge = '<span class="badge badge-kfp">כשל"פ ✓</span>' if is_kfp else '<span class="badge badge-no">ללא כשל"פ</span>'
    row = f"<tr><td class='prod-name'>{PROD_HEB[p]}</td><td>{kfp_badge}</td>"
    for w in weekly:
        reg = w['reg_sold_p'][p]
        kfp = w['kfp_sold_p'][p]
        cell_class = "kfp-cell" if kfp > 0 else ""
        kfp_str = f"<span class='kfp-num'>+{kfp:.1f} כשל\"פ</span>" if kfp > 0 else ""
        row += f"<td class='{cell_class}'><span class='reg-num'>{reg:.1f}</span>{kfp_str}</td>"
    row += "</tr>"
    table_rows += row

# Balance row
for p in PRODUCTS:
    row = f"<tr class='bal-row'><td colspan='2' class='bal-label'>יתרה סוף שבוע — {PROD_HEB[p]}</td>"
    for w in weekly:
        rb = w['reg_bal_p'][p]
        kb = w['kfp_bal_p'][p]
        kfp_b = f"<span class='kfp-num'>{kb:.1f}✡</span>" if kb > 0 else ""
        row += f"<td><small>{rb:.1f}🔵 {kfp_b}</small></td>"
    row += "</tr>"
    table_rows += row

prod_timeline_html = "".join(f"<li>{e}</li>" for e in prod_events)
week_headers = "".join(f"<th>{w['label_short']}</th>" for w in weekly)

html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>צפי מכר פסח 2026 — גלידת דני אבדיה</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f6fa; color: #1a1a2e; direction: rtl; }}

  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    color: white; padding: 28px 40px; border-bottom: 4px solid #e94560;
  }}
  .header h1 {{ font-size: 1.8rem; font-weight: 700; letter-spacing: 0.5px; }}
  .header .subtitle {{ font-size: 0.95rem; opacity: 0.75; margin-top: 4px; }}

  .kpis {{
    display: flex; gap: 16px; padding: 20px 40px; background: #fff;
    border-bottom: 1px solid #e0e0e0; flex-wrap: wrap;
  }}
  .kpi {{
    flex: 1; min-width: 150px; background: #f8f9fc; border-radius: 10px;
    padding: 14px 18px; border-right: 4px solid #0f3460;
  }}
  .kpi.kfp  {{ border-right-color: #e8c84b; background: #fffdf0; }}
  .kpi.warn {{ border-right-color: #e94560; background: #fff5f7; }}
  .kpi .val {{ font-size: 1.7rem; font-weight: 800; color: #0f3460; }}
  .kpi.kfp .val {{ color: #b8860b; }}
  .kpi.warn .val {{ color: #c0392b; }}
  .kpi .lbl {{ font-size: 0.78rem; color: #666; margin-top: 3px; }}

  .section {{ padding: 24px 40px; }}
  .section-title {{
    font-size: 1.1rem; font-weight: 700; color: #0f3460;
    margin-bottom: 16px; padding-bottom: 8px;
    border-bottom: 2px solid #e94560; display: inline-block;
  }}

  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}

  .chart-card {{
    background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  }}
  .chart-card h3 {{ font-size: 0.92rem; color: #444; margin-bottom: 14px; font-weight: 600; }}

  .kfp-highlight {{
    background: linear-gradient(135deg, #fffbea, #fff7cc);
    border: 2px solid #e8c84b; border-radius: 12px; padding: 16px 20px;
    margin-bottom: 24px;
  }}
  .kfp-highlight h3 {{ color: #8b6914; font-size: 0.95rem; margin-bottom: 10px; }}
  .kfp-highlight ul {{ list-style: none; display: flex; gap: 12px; flex-wrap: wrap; }}
  .kfp-highlight li {{
    background: rgba(255,255,255,0.8); border: 1px solid #e8c84b;
    border-radius: 6px; padding: 6px 12px; font-size: 0.84rem; color: #5a4a00;
    font-weight: 600;
  }}

  .no-mango {{
    background: #fff0f4; border: 2px solid #e94560; border-radius: 12px;
    padding: 14px 20px; margin-bottom: 24px;
    font-size: 0.88rem; color: #8b0000;
  }}
  .no-mango strong {{ font-size: 1rem; }}

  table {{
    width: 100%; border-collapse: collapse; font-size: 0.83rem;
    background: white; border-radius: 10px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  }}
  th {{
    background: #0f3460; color: white; padding: 10px 12px;
    text-align: center; font-weight: 600;
  }}
  td {{ padding: 8px 12px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #f8f9fc; }}
  .prod-name {{ font-weight: 700; text-align: right; padding-right: 16px; }}
  .kfp-cell {{ background: #fffcee; }}
  .kfp-num {{ color: #b8860b; font-size: 0.78rem; display: block; font-weight: 700; }}
  .reg-num {{ color: #1a1a2e; font-weight: 600; }}
  .badge {{ border-radius: 20px; padding: 3px 8px; font-size: 0.72rem; font-weight: 700; }}
  .badge-kfp  {{ background: #fff3cd; color: #856404; border: 1px solid #ffc107; }}
  .badge-no   {{ background: #f0f0f0; color: #666; border: 1px solid #ccc; }}
  .bal-row td {{ background: #f8f9fc; font-size: 0.78rem; color: #555; }}
  .bal-label  {{ text-align: right; color: #888; font-style: italic; padding-right: 16px; }}

  .window-bar {{
    display: flex; align-items: center; gap: 10px; padding: 10px 40px;
    background: #fff; border-top: 1px solid #eee; font-size: 0.83rem;
  }}
  .window-seg {{
    flex: 1; height: 36px; border-radius: 6px; display: flex;
    align-items: center; justify-content: center; font-weight: 700; font-size: 0.78rem;
  }}
  .seg-pre  {{ background: #e8eaf6; color: #3949ab; flex: 0.7; }}
  .seg-prod {{ background: #fff3e0; color: #e65100; flex: 0.35; }}
  .seg-kfp  {{ background: linear-gradient(135deg, #fff8dc, #ffd700); color: #7b5800;
               border: 2px solid #ffd700; flex: 1.8; font-size: 0.85rem; }}
  .seg-post {{ background: #e8f5e9; color: #2e7d32; flex: 1.2; }}
  .seg-label {{ font-size: 0.72rem; color: #999; white-space: nowrap; }}

  footer {{
    text-align: center; padding: 16px; color: #aaa; font-size: 0.78rem;
    border-top: 1px solid #eee; margin-top: 20px;
  }}

  /* ── Distributor table ─────────────────────────────────────────── */
  .dist-table {{
    width: 100%; border-collapse: collapse; font-size: 0.83rem;
    background: white; border-radius: 10px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-top: 20px;
  }}
  .dist-table th {{
    background: #16213e; color: white; padding: 10px 12px;
    text-align: center; font-weight: 600;
  }}
  .dist-table td {{ padding: 8px 12px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
  .dist-table tr:hover td {{ background: #f8f9fc; }}
  .dist-name {{ font-weight: 700; text-align: right; padding-right: 16px; color: #0f3460; }}
  .total-col {{ font-weight: 700; background: #f0f4ff; }}
  .subtotal-row td {{ background: #e8edf8; font-weight: 700; color: #16213e; }}
  .subtotal {{ font-weight: 700; }}
  .grand-row td {{ background: #16213e; color: white; font-weight: 800; }}
  .grand-total {{ font-weight: 800; }}
  .dist-chart-wrap {{ background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07); margin-bottom: 24px; }}
</style>
</head>
<body>

<div class="header">
  <h1>📊 צפי מכר שבועי — פסח 2026</h1>
  <div class="subtitle">גלידת חלבון · דני אבדיה / Turbo · מחולק למלאי כשר לפסח ומלאי רגיל</div>
</div>

<!-- Timeline bar -->
<div class="window-bar">
  <span class="seg-label">01/03</span>
  <div class="window-seg seg-pre">לפני חלון כשל"פ</div>
  <div class="window-seg seg-prod">ייצור כשל"פ<br><small>08–12/03</small></div>
  <div class="window-seg seg-kfp">⭐ חלון מכירות כשל"פ ⭐<br><small>09/03 – 26/03</small></div>
  <div class="window-seg seg-post">חזרה לרגיל · ערב פסח 12/04</div>
  <span class="seg-label">09/04</span>
</div>

<!-- KPIs -->
<div class="kpis">
  <div class="kpi kfp">
    <div class="val">{total_kfp_prod}</div>
    <div class="lbl">משטחים כשל"פ לייצור<br>(שוקולד+וניל+פיסטוק × 6 כ"א)</div>
  </div>
  <div class="kpi kfp">
    <div class="val">{total_kfp_sold:.0f}</div>
    <div class="lbl">משטחים כשל"פ צפויים להימכר<br>09/03 – 26/03</div>
  </div>
  <div class="kpi">
    <div class="val">{total_reg_avail:.0f}</div>
    <div class="lbl">משטחים מלאי רגיל קיים<br>(מחסן + מפיצים)</div>
  </div>
  <div class="kpi">
    <div class="val">{total_reg_sold:.1f}</div>
    <div class="lbl">משטחים רגיל צפויים להימכר<br>01/03 – 09/04</div>
  </div>
  <div class="kpi warn">
    <div class="val">{reg_remaining:.0f}</div>
    <div class="lbl">משטחים רגיל יתרה אחרי 09/04<br>(כולל מנגו)</div>
  </div>
  <div class="kpi">
    <div class="val">{kfp_remaining:.1f}</div>
    <div class="lbl">משטחים כשל"פ יתרה אחרי 09/04<br>(יעד: 0)</div>
  </div>
</div>

<div class="section">
  <!-- Mango alert -->
  <div class="no-mango">
    🥭 <strong>מנגו — ללא ייצור כשל"פ</strong> | פיסטוק (טעם חדש) צפוי לקחת את נתח הביקוש הפסחי.
    מלאי מנגו רגיל קיים: {round(reg_stock_units['mango']/PALLET, 1)} משטחים — ימשיך להימכר בקצב רגיל לאורך כל התקופה.
  </div>

  <!-- KFP production timeline -->
  <div class="kfp-highlight">
    <h3>⚙️ לוח ייצור כשל"פ (תחילת ייצור 08/03)</h3>
    <ul>{prod_timeline_html}</ul>
  </div>

  <!-- Charts -->
  <span class="section-title">מכירות שבועיות — מלאי כשל"פ vs מלאי רגיל</span>
  <div class="charts-grid">
    <div class="chart-card">
      <h3>📦 משטחים שנמכרו בשבוע (כשל"פ + רגיל לפי מוצר)</h3>
      <canvas id="salesChart" height="280"></canvas>
    </div>
    <div class="chart-card">
      <h3>📉 יתרת מלאי סוף שבוע (משטחים)</h3>
      <canvas id="balanceChart" height="280"></canvas>
    </div>
  </div>
</div>

<!-- Table -->
<div class="section">
  <span class="section-title">טבלת צפי מפורטת — יחידות משטחים לפי שבוע</span>
  <p style="font-size:0.8rem; color:#888; margin-bottom:12px;">
    🔵 מספר כחול = מכירות מלאי רגיל (משטחים) &nbsp;|&nbsp;
    ⭐ מספר זהוב = מכירות מלאי כשל"פ (משטחים) &nbsp;|&nbsp;
    שורות יתרה = מלאי נותר בסוף שבוע
  </p>
  <table>
    <thead>
      <tr>
        <th>מוצר</th><th>כשל"פ?</th>
        {week_headers}
      </tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>
</div>

<!-- Distributor KFP weekly pull section -->
<div class="section">
  <span class="section-title">חלוקת ייצור כשל"פ למפיצים — צפי משיכות שבועי</span>
  <p style="font-size:0.8rem; color:#888; margin-bottom:16px;">
    חלוקה פרופורציונלית לפי צפי מכירות פברואר · 3 שבועות חלון כשל"פ (09/03–26/03) · סה"כ 18 משטחים
  </p>
  <div class="dist-chart-wrap">
    <h3 style="font-size:0.92rem; color:#444; margin-bottom:14px; font-weight:600;">
      📦 צפי משיכות שבועיות — כשל"פ לפי מפיץ ומוצר (משטחים)
    </h3>
    <canvas id="distChart" height="200"></canvas>
  </div>
  {dist_table_html}
</div>

<footer>
  נוצר אוטומטית · Raito · נתוני בסיס: פברואר 2026 MTD · ייצור כשל"פ מ-08/03/2026
</footer>

<script>
// ── Sales stacked bar chart ─────────────────────────────────────────────────
const salesCtx = document.getElementById('salesChart');
const salesData = {{
  labels: {labels_js},
  datasets: {json.dumps(sales_datasets, ensure_ascii=False)}
}};
new Chart(salesCtx, {{
  type: 'bar',
  data: salesData,
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }}, boxWidth: 14 }} }},
      tooltip: {{
        callbacks: {{
          label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(2)}} מש׳`
        }}
      }}
    }},
    scales: {{
      x: {{
        stacked: true,
        ticks: {{ font: {{ size: 11 }}, maxRotation: 0 }},
        grid: {{ display: false }}
      }},
      y: {{
        stacked: true,
        title: {{ display: true, text: 'משטחים' }},
        ticks: {{ font: {{ size: 11 }} }}
      }}
    }}
  }}
}});

// ── Distributor KFP weekly pull chart ───────────────────────────────────────
const distCtx = document.getElementById('distChart');
new Chart(distCtx, {{
  type: 'bar',
  data: {{
    labels: {dist_chart_labels_js},
    datasets: {json.dumps(dist_datasets, ensure_ascii=False)}
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }}, boxWidth: 14 }} }},
      tooltip: {{
        callbacks: {{
          label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(1)}} מש׳`
        }}
      }}
    }},
    scales: {{
      x: {{
        stacked: true,
        ticks: {{ font: {{ size: 12 }}, maxRotation: 0 }},
        grid: {{ display: false }}
      }},
      y: {{
        stacked: true,
        title: {{ display: true, text: 'משטחים' }},
        ticks: {{ font: {{ size: 11 }}, stepSize: 1 }}
      }}
    }}
  }}
}});

// ── Balance line chart ─────────────────────────────────────────────────────
const balCtx = document.getElementById('balanceChart');
const balData = {{
  labels: {labels_js},
  datasets: {json.dumps(bal_datasets, ensure_ascii=False)}
}};
new Chart(balCtx, {{
  type: 'line',
  data: balData,
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ font: {{ size: 10 }}, boxWidth: 14 }} }},
      tooltip: {{
        callbacks: {{
          label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(1)}} מש׳`
        }}
      }}
    }},
    scales: {{
      x: {{
        ticks: {{ font: {{ size: 11 }}, maxRotation: 0 }},
        grid: {{ color: '#f0f0f0' }}
      }},
      y: {{
        title: {{ display: true, text: 'משטחים נותרים' }},
        ticks: {{ font: {{ size: 11 }} }},
        grid: {{ color: '#f0f0f0' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

# ── Save ─────────────────────────────────────────────────────────────────────
OUT = str(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'docs', 'passover_forecast.html'))
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✓ נשמר: {OUT}")

# ── Print weekly table to console ────────────────────────────────────────────
import pandas as pd
rows = []
for w in weekly:
    for p in PRODUCTS:
        rows.append({
            'שבוע': w['label_short'],
            'מוצר': PROD_HEB[p],
            'רגיל (מש׳)': w['reg_sold_p'][p],
            'כשל"פ (מש׳)': w['kfp_sold_p'][p],
            'יתרה רגיל': w['reg_bal_p'][p],
            'יתרה כשל"פ': w['kfp_bal_p'][p],
        })
df = pd.DataFrame(rows)
print("\n" + "=" * 90)
print("  צפי מכר שבועי — פסח 2026")
print("=" * 90)
print(df.to_string(index=False))
print()
print(f"  סה\"כ כשל\"פ נמכר:  {total_kfp_sold:.1f} מש׳  |  יתרה כשל\"פ: {kfp_remaining:.1f} מש׳")
print(f"  סה\"כ רגיל נמכר:   {total_reg_sold:.1f} מש׳  |  יתרה רגיל:  {reg_remaining:.1f} מש׳")
