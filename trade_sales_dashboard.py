#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trade & Sales Dashboard — Customer-Centric HTML Generator
Generates: docs/trade_and_sales_dashboard.html

Data quality fixes:
- Deduplicate customers (וולט/וואלט, ינגו variants)
- Remove branch-level entries (containing *ת or ת.משלוח)
- Skip entries with *לא להקלדה
- Combine icedream + mayyan data
"""

import json
import sys
import math
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from parsers import consolidate_data
from config import (
    SELLING_PRICE_B2B, PRODUCTION_COST, PRODUCT_NAMES, PRODUCT_SHORT,
    PRODUCT_COLORS, PRODUCTS_ORDER, OUTPUT_DIR
)

# ── Constants ──────────────────────────────────────────────────────────────────
DIST_COST_PCT   = 0.15   # Default distributor cost percentage
MONTHS_ORDER    = ['December 2025', 'January 2026', 'February 2026']
MONTH_SHORT     = {
    'December 2025': "Dec '25",
    'January 2026': "Jan '26",
    'February 2026': "Feb '26",
}
PRODUCT_HEB     = {
    'chocolate': 'שוקולד',
    'vanilla': 'וניל',
    'mango': 'מנגו',
    'pistachio': 'פיסטוק',
    'dream_cake': 'עוגת חלום',
    'magadat': 'מארז'
}
PRODUCT_CLR = PRODUCT_COLORS
DIST_COST = {
    'icedream': 0.15,
    'mayyan': 0.12
}

# ── Data Cleaning Functions ────────────────────────────────────────────────────

def is_branch_entry(name):
    """Check if entry is a branch location (contains *ת or ת.משלוח)."""
    if not name:
        return False
    name_str = str(name)
    return '*ת' in name_str or 'ת.משלוח' in name_str


def is_skip_entry(name):
    """Check if entry should be skipped (*לא להקלדה)."""
    if not name:
        return False
    name_str = str(name)
    return '*לא להקלדה' in name_str or 'לא להקלדה' in name_str


def normalize_customer_name(name):
    """Normalize customer names for deduplication."""
    if not name:
        return None
    name_str = str(name).strip()
    
    # וולט / וואלט deduplication → "וולט"
    if name_str == "וואלט אופריישנס סרוויסס ישראל  בע\"מ -   *לא להקלדה":
        return None  # Skip this variant entirely
    if 'וואלט' in name_str or 'וולט' in name_str:
        return "וולט"
    
    # ינגו deduplication → "ינגו דלי ישראל בע"מ"
    if name_str == "ינגו":
        return "ינגו דלי ישראל בע\"מ"
    if name_str == "ינגו דלי ישראל בע\"מ":
        return "ינגו דלי ישראל בע\"מ"
    
    return name_str


def clean_icedream_customers(customers_dict):
    """
    Clean icedream customer data:
    - Remove branch entries (*ת, ת.משלוח)
    - Skip entries with *לא להקלדה
    - Deduplicate (וולט/וואלט, ינגו variants)
    """
    cleaned = {}
    
    for cname, prods in customers_dict.items():
        # Skip branch entries and entries with *לא להקלדה
        if is_branch_entry(cname) or is_skip_entry(cname):
            continue
        
        # Normalize name for deduplication
        normalized = normalize_customer_name(cname)
        if normalized is None:
            continue
        
        # Aggregate if normalized name already exists
        if normalized not in cleaned:
            cleaned[normalized] = {}
        
        for prod, pdata in prods.items():
            if normalized not in cleaned:
                cleaned[normalized] = {}
            if prod not in cleaned[normalized]:
                cleaned[normalized][prod] = {'units': 0, 'value': 0, 'cartons': 0}
            
            if isinstance(pdata, dict):
                cleaned[normalized][prod]['units'] = max(cleaned[normalized][prod]['units'], pdata.get('units', 0))
                cleaned[normalized][prod]['value'] = max(cleaned[normalized][prod]['value'], pdata.get('value', 0))
                cleaned[normalized][prod]['cartons'] = max(cleaned[normalized][prod]['cartons'], pdata.get('cartons', 0))
    
    return cleaned


# ── Financial Functions ────────────────────────────────────────────────────────

def gross_margin_pct(product):
    """Calculate gross margin percentage for a product."""
    price = SELLING_PRICE_B2B.get(product, 13.8)
    cost = PRODUCTION_COST.get(product, 6.5)
    return (price - cost) / price if price else 0


def build_customer_data(raw_data):
    """Build per-customer monthly metrics for both distributors."""
    customers = {}  # key = (distributor, customer_name)

    for month in MONTHS_ORDER:
        md = raw_data['monthly_data'].get(month, {})

        # ── Icedream customers (cleaned) ──
        ice_custs = clean_icedream_customers(md.get('icedreams_customers', {}))
        for cname, prods in ice_custs.items():
            key = ('icedream', cname)
            if key not in customers:
                customers[key] = {'distributor': 'icedream', 'name': cname, 'months': {}}
            
            revenue = gross_p = op_p = units = 0
            product_units = {}
            
            for prod, pd in prods.items():
                if not isinstance(pd, dict):
                    continue
                u = pd.get('units', 0)
                v = pd.get('value', 0)
                gm_pct = gross_margin_pct(prod)
                gm = v * gm_pct
                
                revenue += v
                gross_p += gm
                op_p += gm - (v * DIST_COST['icedream'])
                units += u
                product_units[prod] = product_units.get(prod, 0) + u
            
            if revenue > 0:
                customers[key]['months'][month] = {
                    'revenue': round(revenue, 2),
                    'gross_profit': round(gross_p, 2),
                    'op_profit': round(op_p, 2),
                    'units': units,
                    'products': product_units,
                }

        # ── Mayyan chains ──
        for chain, prods in md.get('mayyan_chains', {}).items():
            if not isinstance(prods, dict):
                continue
            
            key = ('mayyan', chain)
            if key not in customers:
                customers[key] = {'distributor': 'mayyan', 'name': chain, 'months': {}}
            
            revenue = gross_p = op_p = units = 0
            product_units = {}
            
            for prod, val in prods.items():
                # mayyan_chains stores units directly (int) or dict
                if isinstance(val, dict):
                    u = val.get('units', 0)
                elif isinstance(val, (int, float)):
                    u = val
                else:
                    continue
                
                price = SELLING_PRICE_B2B.get(prod, 13.8)
                v = u * price
                gm_pct = gross_margin_pct(prod)
                gm = v * gm_pct
                
                revenue += v
                gross_p += gm
                op_p += gm - (v * DIST_COST['mayyan'])
                units += u
                product_units[prod] = product_units.get(prod, 0) + u
            
            if revenue > 0:
                customers[key]['months'][month] = {
                    'revenue': round(revenue, 2),
                    'gross_profit': round(gross_p, 2),
                    'op_profit': round(op_p, 2),
                    'units': units,
                    'products': product_units,
                }

    return customers


def aggregate_customer(cdata):
    """Aggregate a customer's all-time totals and compute MoM."""
    months = cdata['months']
    totals = {
        'revenue': 0,
        'gross_profit': 0,
        'op_profit': 0,
        'units': 0,
        'products': {}
    }
    
    for md in months.values():
        totals['revenue'] += md['revenue']
        totals['gross_profit'] += md['gross_profit']
        totals['op_profit'] += md['op_profit']
        totals['units'] += md['units']
        for p, u in md.get('products', {}).items():
            totals['products'][p] = totals['products'].get(p, 0) + u

    totals['gm_pct'] = (totals['gross_profit'] / totals['revenue'] * 100
                        if totals['revenue'] else 0)

    # MoM: compare Jan vs Dec (or Feb vs Jan)
    sorted_months = [m for m in MONTHS_ORDER if m in months]
    mom = 0
    if len(sorted_months) >= 2:
        cur = months[sorted_months[-1]]['revenue']
        prev = months[sorted_months[-2]]['revenue']
        mom = (cur - prev) / prev * 100 if prev else 0
    
    totals['mom'] = round(mom, 1)
    totals['month_count'] = len(sorted_months)
    return totals


def build_portfolio_trend(raw_data):
    """Monthly totals across all brands for trend charts."""
    trend = []
    for month in MONTHS_ORDER:
        md = raw_data['monthly_data'].get(month, {})
        combined = md.get('combined', {})
        rev = sum(v.get('total_value', 0) for v in combined.values() if isinstance(v, dict))
        units = sum(v.get('units', 0) for v in combined.values() if isinstance(v, dict))
        trend.append({
            'month': MONTH_SHORT[month],
            'revenue': round(rev),
            'units': units
        })
    return trend


# ── SVG Chart Functions ────────────────────────────────────────────────────────

def svg_bar_chart(labels, values, colors, width=580, height=240):
    """Generate SVG vertical bar chart."""
    if not labels:
        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"><text x="10" y="30" fill="#9096a8" font-size="12">No data</text></svg>'
    
    # Find max value for scaling
    max_val = max(values) if values else 1
    if max_val == 0:
        max_val = 1
    
    padding = 40
    plot_width = width - padding - 20
    plot_height = height - padding - 30
    bar_width = max(8, plot_width / (len(labels) * 1.5))
    gap = bar_width * 0.3
    
    svg_parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<defs><style>text { font-family: Segoe UI, sans-serif; font-size: 11px; } .axis-text { fill: #9096a8; } .label-text { fill: #e8eaf0; }</style></defs>',
    ]
    
    # Y-axis line
    svg_parts.append(f'<line x1="{padding}" y1="10" x2="{padding}" y2="{height - 30}" stroke="#2a2d3e" stroke-width="1"/>')
    
    # X-axis line
    svg_parts.append(f'<line x1="{padding}" y1="{height - 30}" x2="{width - 10}" y2="{height - 30}" stroke="#2a2d3e" stroke-width="1"/>')
    
    # Y-axis labels and grid
    for i in range(5):
        y_val = int(max_val * (4 - i) / 4)
        y_pos = 10 + i * (plot_height / 4)
        svg_parts.append(f'<text x="{padding - 5}" y="{y_pos + 4}" text-anchor="end" class="axis-text">{y_val:,}</text>')
        if i > 0:
            svg_parts.append(f'<line x1="{padding}" y1="{y_pos}" x2="{width - 10}" y2="{y_pos}" stroke="#1e2235" stroke-width="1" stroke-dasharray="2,2"/>')
    
    # Bars
    for idx, (label, value) in enumerate(zip(labels, values)):
        x = padding + 10 + idx * (bar_width + gap)
        bar_height = (value / max_val) * plot_height if max_val > 0 else 0
        y = height - 30 - bar_height
        color = colors[idx] if idx < len(colors) else '#3b82f6'
        
        svg_parts.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="2"/>')
        
        # Truncated label
        label_text = label[:12] + ('...' if len(label) > 12 else '')
        svg_parts.append(f'<text x="{x + bar_width/2}" y="{height - 12}" text-anchor="middle" class="label-text">{label_text}</text>')
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def svg_line_chart(labels, values, width=580, height=240):
    """Generate SVG line chart."""
    if not labels or not values:
        return f'<svg width="{width}" height="{height}"><text x="10" y="30" fill="#9096a8">No data</text></svg>'
    
    max_val = max(values) if values else 1
    if max_val == 0:
        max_val = 1
    
    padding = 40
    plot_width = width - padding - 20
    plot_height = height - padding - 30
    
    # Calculate points
    points = []
    for idx, (label, value) in enumerate(zip(labels, values)):
        x = padding + (idx / (len(labels) - 1) if len(labels) > 1 else 0.5) * plot_width
        y = height - 30 - (value / max_val) * plot_height
        points.append((x, y, label, value))
    
    svg_parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<defs><style>text { font-family: Segoe UI, sans-serif; font-size: 11px; } .axis-text { fill: #9096a8; } .label-text { fill: #e8eaf0; }</style></defs>',
    ]
    
    # Axes
    svg_parts.append(f'<line x1="{padding}" y1="10" x2="{padding}" y2="{height - 30}" stroke="#2a2d3e" stroke-width="1"/>')
    svg_parts.append(f'<line x1="{padding}" y1="{height - 30}" x2="{width - 10}" y2="{height - 30}" stroke="#2a2d3e" stroke-width="1"/>')
    
    # Y-axis labels
    for i in range(5):
        y_val = int(max_val * (4 - i) / 4)
        y_pos = 10 + i * (plot_height / 4)
        svg_parts.append(f'<text x="{padding - 5}" y="{y_pos + 4}" text-anchor="end" class="axis-text">{y_val:,}</text>')
    
    # Line
    if points:
        path_d = ' '.join([f'{"M" if idx == 0 else "L"} {x} {y}' for idx, (x, y, _, _) in enumerate(points)])
        svg_parts.append(f'<path d="{path_d}" stroke="#3b82f6" stroke-width="2" fill="none"/>')
        
        # Fill area
        area_path = f'M {points[0][0]} {height - 30} ' + path_d + f' L {points[-1][0]} {height - 30} Z'
        svg_parts.append(f'<path d="{area_path}" fill="#3b82f6" opacity="0.15"/>')
        
        # Points
        for x, y, _, _ in points:
            svg_parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#3b82f6" stroke="white" stroke-width="1"/>')
        
        # X-axis labels
        for x, y, label, _ in points:
            svg_parts.append(f'<text x="{x}" y="{height - 12}" text-anchor="middle" class="label-text">{label}</text>')
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


# ── HTML Generation ───────────────────────────────────────────────────────────

def build_dashboard(raw_data):
    """Build complete dashboard HTML."""
    customers_raw = build_customer_data(raw_data)
    portfolio_trend = build_portfolio_trend(raw_data)

    # Build serializable customer list
    cust_list = []
    for (dist, name), cdata in customers_raw.items():
        agg = aggregate_customer(cdata)
        if agg['revenue'] < 1:
            continue
        
        cust_list.append({
            'dist': dist,
            'name': name,
            'revenue': round(agg['revenue']),
            'gross_profit': round(agg['gross_profit']),
            'op_profit': round(agg['op_profit']),
            'gm_pct': round(agg['gm_pct'], 1),
            'units': agg['units'],
            'mom': agg['mom'],
            'products': agg['products'],
            'months': {
                MONTH_SHORT.get(m, m): {
                    'revenue': round(v['revenue']),
                    'units': v['units'],
                }
                for m, v in cdata['months'].items()
            },
        })

    # Sort by revenue desc
    cust_list.sort(key=lambda x: x['revenue'], reverse=True)

    # Global KPIs
    total_rev = sum(c['revenue'] for c in cust_list)
    total_gp = sum(c['gross_profit'] for c in cust_list)
    total_op = sum(c['op_profit'] for c in cust_list)
    total_u = sum(c['units'] for c in cust_list)
    total_cust = len(cust_list)
    avg_gm = total_gp / total_rev * 100 if total_rev else 0

    # Latest month KPIs (Jan 2026)
    jan_rev = jan_units = jan_gp = jan_op = jan_cust = 0
    jan_key = "Jan '26"
    
    for c in cust_list:
        m = c['months'].get(jan_key, {})
        if m.get('revenue', 0):
            jan_rev += m['revenue']
            jan_units += m['units']
            jan_cust += 1
    
    for (dist, name), cdata in customers_raw.items():
        jan = cdata['months'].get('January 2026', {})
        jan_gp += jan.get('gross_profit', 0)
        jan_op += jan.get('op_profit', 0)

    # Portfolio MoM (Dec→Jan)
    portfolio_mom = 0
    if len(portfolio_trend) >= 2:
        cur_r = portfolio_trend[1]['revenue']
        prev_r = portfolio_trend[0]['revenue']
        portfolio_mom = (cur_r - prev_r) / prev_r * 100 if prev_r else 0

    now_str = datetime.now().strftime('%d %b %Y %H:%M')
    
    # Prepare chart data
    top_15 = sorted(cust_list, key=lambda x: x['revenue'], reverse=True)[:15]
    pareto_labels = [c['name'] for c in top_15]
    pareto_values = [c['revenue'] for c in top_15]
    pareto_colors = [
        '#10b981' if c['gm_pct'] >= 45 else '#f59e0b' if c['gm_pct'] >= 40 else '#ef4444'
        for c in top_15
    ]
    pareto_svg = svg_bar_chart(pareto_labels, pareto_values, pareto_colors)

    # Portfolio trend chart
    trend_labels = [t['month'] for t in portfolio_trend]
    trend_values = [t['revenue'] for t in portfolio_trend]
    trend_svg = svg_line_chart(trend_labels, trend_values)

    data_js = json.dumps({
        'customers': cust_list,
        'portfolioTrend': portfolio_trend,
        'productColors': PRODUCT_CLR,
        'productShort': PRODUCT_SHORT,
        'productHeb': PRODUCT_HEB,
    }, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="he" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trade & Sales Dashboard</title>
<style>
:root {{
  --bg: #0f1117;
  --card: #1a1d2e;
  --card2: #1e2235;
  --border: #2a2d3e;
  --text: #e8eaf0;
  --text2: #9096a8;
  --accent: #3b82f6;
  --green: #10b981;
  --red: #ef4444;
  --amber: #f59e0b;
  --header-h: #161929;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: 'Segoe UI', Tahoma, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
}}

/* Header */
.hdr {{
  background: var(--header-h);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}}

.hdr-left h1 {{
  font-size: 18px;
  font-weight: 700;
}}

.hdr-left .sub {{
  color: var(--text2);
  font-size: 12px;
  margin-top: 2px;
}}

.hdr-badges {{
  display: flex;
  gap: 8px;
  align-items: center;
}}

.badge {{
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}}

.badge-grey {{
  background: #2a2d3e;
  color: var(--text2);
}}

.badge-green {{
  background: #064e3b;
  color: #34d399;
  border: 1px solid #059669;
}}

.badge-amber {{
  background: #78350f;
  color: #fcd34d;
  border: 1px solid #d97706;
}}

/* Filter Bar */
.fbar {{
  padding: 16px 24px;
  background: var(--card);
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}}

.fbar label {{
  font-weight: 600;
  color: var(--text2);
  font-size: 12px;
  white-space: nowrap;
}}

.fbar select, .fbar button {{
  padding: 6px 12px;
  border: 1px solid var(--border);
  background: var(--card2);
  color: var(--text);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}}

.fbar select:hover, .fbar button:hover {{
  background: #2a2d3e;
}}

.brand-btn {{
  background: var(--card2);
  border: 1px solid var(--border);
  color: var(--text2);
}}

.brand-btn.active {{
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}}

.reset-btn {{
  margin-left: auto;
  background: #7f1d1d;
  border-color: #991b1b;
  color: #fca5a5;
}}

.reset-btn:hover {{
  background: #991b1b;
}}

/* Banner */
.banner {{
  padding: 12px 24px;
  background: #064e3b;
  color: #34d399;
  border-bottom: 1px solid #059669;
  display: flex;
  align-items: center;
  gap: 8px;
}}

.banner .chk {{
  font-weight: 700;
  font-size: 16px;
}}

/* KPIs */
.kpis {{
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  padding: 20px 24px;
  background: var(--bg);
}}

.kpi {{
  background: var(--card);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
}}

.kpi .label {{
  color: var(--text2);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 8px;
}}

.kpi .val {{
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}}

.kpi .val.green {{ color: var(--green); }}
.kpi .val.red {{ color: var(--red); }}

.kpi .sub {{
  color: var(--text2);
  font-size: 11px;
}}

.pos {{ color: var(--green); }}
.neg {{ color: var(--red); }}

/* Charts */
.grid2 {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 0 24px 16px;
}}

.grid3 {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 0 24px 16px;
}}

.chart-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}}

.chart-card.full {{
  grid-column: 1 / -1;
}}

.chart-title {{
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 4px;
}}

.chart-sub {{
  color: var(--text2);
  font-size: 11px;
  margin-bottom: 12px;
}}

canvas {{
  width: 100%;
  height: auto;
  display: block;
}}

.legend {{
  display: flex;
  gap: 16px;
  margin-top: 12px;
  flex-wrap: wrap;
}}

.legend-item {{
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text2);
}}

.legend-sq {{
  width: 12px;
  height: 12px;
  border-radius: 2px;
}}

/* Table */
.tbl-wrap {{
  overflow-x: auto;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}

th {{
  background: var(--card2);
  padding: 10px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
}}

th:hover {{
  background: #2a2d3e;
}}

td {{
  padding: 10px;
  border-bottom: 1px solid var(--border);
}}

tr:hover {{
  background: var(--card2);
}}

.rag-g {{
  color: var(--green);
  font-weight: 600;
}}

.rag-a {{
  color: var(--amber);
  font-weight: 600;
}}

.rag-r {{
  color: var(--red);
  font-weight: 600;
}}

.mom-pos {{
  color: var(--green);
}}

.mom-neg {{
  color: var(--red);
}}

.ts {{
  text-align: center;
  padding: 16px;
  color: var(--text2);
  font-size: 11px;
}}

@media (max-width: 900px) {{
  .kpis {{ grid-template-columns: repeat(2, 1fr); }}
  .grid2, .grid3 {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<!-- Header -->
<div class="hdr">
  <div class="hdr-left">
    <h1>Trade &amp; Sales Dashboard</h1>
    <div class="sub">Customer-Centric &middot; Dec '25 – Feb '26</div>
  </div>
  <div class="hdr-badges">
    <span class="badge badge-grey">ISR</span>
    <span class="badge badge-grey">Ice Cream / Frozen</span>
    <span class="badge badge-green">&#9679; Sales Data Loaded</span>
    <span class="badge badge-amber">Feb = MTD</span>
  </div>
</div>

<!-- Filter Bar -->
<div class="fbar">
  <label>Customer</label>
  <select id="sel-customer" onchange="applyFilters()">
    <option value="__all__">All Customers</option>
  </select>

  <label>Distributor</label>
  <select id="sel-dist" onchange="applyFilters()">
    <option value="__all__">All Distributors</option>
    <option value="icedream">אייסקרים (Icedream)</option>
    <option value="mayyan">מעיין (Ma'ayan)</option>
  </select>

  <label>Status</label>
  <select id="sel-status" onchange="applyFilters()">
    <option value="__all__">All</option>
    <option value="active">Active (MoM &gt; 0%)</option>
    <option value="growing">Growing (&gt; 10%)</option>
    <option value="declining">Declining (&lt; 0%)</option>
  </select>

  <label>Month</label>
  <select id="sel-month" onchange="applyFilters()">
    <option value="__all__">All Months</option>
    <option value="Dec '25">December '25</option>
    <option value="Jan '26">January '26</option>
    <option value="Feb '26">February '26</option>
  </select>

  <label>Brand</label>
  <button class="brand-btn active" id="btn-ab" onclick="setBrand('ab')">All Brands</button>
  <button class="brand-btn" id="btn-turbo" onclick="setBrand('turbo')">Turbo</button>
  <button class="brand-btn" id="btn-danis" onclick="setBrand('danis')">Dani's</button>

  <button class="reset-btn" onclick="resetFilters()">Reset</button>
</div>

<!-- Info Banner -->
<div class="banner">
  <span class="chk">✓</span>
  <span id="banner-text">Sales data loaded — Dec '25, Jan '26, Feb '26 (MTD) · <b>42</b> customers · 2 distributors</span>
</div>

<!-- KPI Cards -->
<div class="kpis">
  <div class="kpi">
    <div class="label">Revenue (Jan)</div>
    <div class="val" id="kpi-rev">₪0</div>
    <div class="sub" id="kpi-rev-sub"><span class="pos">+0.0% vs prev</span></div>
  </div>

  <div class="kpi">
    <div class="label">Units (Jan)</div>
    <div class="val" id="kpi-units">0</div>
    <div class="sub" id="kpi-units-sub">0 customers w/ sales</div>
  </div>

  <div class="kpi">
    <div class="label">Gross Profit ₪</div>
    <div class="val green" id="kpi-gp">₪0</div>
    <div class="sub" id="kpi-gp-sub">Avg Gross: 0%</div>
  </div>

  <div class="kpi">
    <div class="label">OP Profit ₪</div>
    <div class="val green" id="kpi-op">₪0</div>
    <div class="sub">After dist. costs</div>
  </div>

  <div class="kpi">
    <div class="label">Customers w/ Sales</div>
    <div class="val" id="kpi-cust">0</div>
    <div class="sub" id="kpi-cust-sub">of 0 in filter</div>
  </div>

  <div class="kpi">
    <div class="label">Portfolio Dec→Jan</div>
    <div class="val" id="kpi-mom">+0.0%</div>
    <div class="sub">MoM change</div>
  </div>
</div>

<!-- Charts: Row 1 (Pareto + Quadrant) -->
<div style="display:grid;grid-template-columns:3fr 2fr;gap:16px;padding:0 24px 16px">
  <div class="chart-card">
    <div class="chart-title">Customer Revenue Ranking — Pareto</div>
    <div class="chart-sub">Top 15 customers by revenue. GM% RAG: Green ≥45%, Amber 40-44%, Red &lt;40%</div>
    <canvas id="paretoChart" height="280"></canvas>
    <div class="legend">
      <div class="legend-item"><div class="legend-sq" style="background: #10b981;"></div> Healthy (GM% ≥ 45%)</div>
      <div class="legend-item"><div class="legend-sq" style="background: #f59e0b;"></div> Caution (40-44%)</div>
      <div class="legend-item"><div class="legend-sq" style="background: #ef4444;"></div> At Risk (GM% &lt; 40%)</div>
    </div>
  </div>

  <div class="chart-card">
    <div class="chart-title">Growth Quadrant</div>
    <div class="chart-sub">Revenue vs MoM%</div>
    <canvas id="quadrantChart" height="280"></canvas>
  </div>
</div>

<!-- Charts: Row 2 (Product Mix + Trend) -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:0 24px 16px">
  <div class="chart-card">
    <div class="chart-title">Product Mix</div>
    <div class="chart-sub">Top 12 customers by units</div>
    <canvas id="mixChart" height="280"></canvas>
  </div>

  <div class="chart-card">
    <div class="chart-title">Portfolio Trend</div>
    <div class="chart-sub">3-month revenue evolution</div>
    <canvas id="trendChart" height="280"></canvas>
  </div>
</div>

<!-- Table Section -->
<div style="padding: 0 24px 24px;">
  <div class="chart-card full">
    <div class="chart-title">Customer Performance Table</div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th onclick="sortTable('name')">Customer</th>
            <th onclick="sortTable('dist')">Distributor</th>
            <th onclick="sortTable('revenue')">Revenue ₪</th>
            <th onclick="sortTable('gm_pct')">GM%</th>
            <th onclick="sortTable('op_profit')">OP Profit ₪</th>
            <th onclick="sortTable('units')">Units</th>
            <th onclick="sortTable('mom')">MoM%</th>
          </tr>
        </thead>
        <tbody id="custTbody">
          <tr><td class="ts" colspan="7">Loading data...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
// ── Global State ──────────────────────────────────────────────────────────
const RAW = {json.dumps({
    'customers': cust_list,
    'portfolioTrend': portfolio_trend,
    'productColors': PRODUCT_CLR,
    'productShort': PRODUCT_SHORT,
    'productHeb': PRODUCT_HEB,
}, ensure_ascii=False)};

let DIST_FILTER = '__all__';
let CUST_FILTER = '__all__';
let MONTH_FILTER = '__all__';
let STATUS_FILTER = '__all__';
let BRAND_FILTER = 'ab';
let SORT_KEY = 'revenue';
let SORT_DIR = -1;
let TREND_MODE = 'revenue';

const TURBO_PRODS = ['chocolate', 'vanilla', 'mango', 'pistachio', 'magadat'];
const DANIS_PRODS = ['dream_cake'];

// ── Utilities ──────────────────────────────────────────────────────────────
function fmt(n) {{ return (n || 0).toLocaleString(); }}
function fmtN(n) {{ return Math.round(n).toLocaleString(); }}

function ragColor(gmPct) {{
  if (gmPct >= 45) return '#10b981';
  if (gmPct >= 40) return '#f59e0b';
  return '#ef4444';
}}

function rag(gmPct) {{
  if (gmPct >= 45) return 'rag-g';
  if (gmPct >= 40) return 'rag-a';
  return 'rag-r';
}}

function fmtAxis(n) {{
  if (n >= 1000000) return '₪' + (n/1000000).toFixed(1) + 'M';
  if (n >= 1000) return '₪' + Math.round(n/1000) + 'K';
  return '₪' + Math.round(n);
}}

function canvasText(ctx, text, x, y, opts={{}}) {{
  ctx.fillStyle = opts.color || '#9096a8';
  ctx.font = `${{opts.bold?'bold ':''}}${{opts.fontSize||11}}px Segoe UI, sans-serif`;
  ctx.textAlign = opts.align || 'left';
  ctx.textBaseline = opts.baseline || 'top';
  ctx.fillText(text, x, y);
}}

// ── Canvas Drawing Helpers ────────────────────────────────────────────────
function drawChart(canvasId, drawFn) {{
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const parent = canvas.parentElement;
  const w = parent.offsetWidth - 32;
  const h = canvas.height || 280;
  canvas.width = w;
  canvas.height = h;
  
  ctx.fillStyle = '#1a1d2e';
  ctx.fillRect(0, 0, w, h);
  
  drawFn(ctx, w, h);
}}

// ── Chart Drawing Functions ──────────────────────────────────────────────

function drawPareto(filtered) {{
  drawChart('paretoChart', (ctx, w, h) => {{
    if (!filtered.length) return;

    const top = [...filtered].sort((a,b) => b.revenue - a.revenue).slice(0, 15);
    const padL = 52, padR = 48, padT = 16, padB = 54;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    const barW = Math.max(18, Math.floor(plotW / top.length) - 3);
    const gap  = Math.max(2, Math.floor(plotW / top.length) - barW);
    const maxVal = Math.max(...top.map(c => c.revenue));
    const totalRev = top.reduce((s, c) => s + c.revenue, 0);

    // Grid lines
    ctx.strokeStyle = '#1e2235';
    ctx.lineWidth = 1;
    for (let i = 1; i <= 4; i++) {{
      const y = padT + plotH * (1 - i/4);
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + plotW, y); ctx.stroke();
    }}

    // Y-axis labels (revenue)
    ctx.textAlign = 'right';
    ctx.fillStyle = '#9096a8';
    ctx.font = '10px Segoe UI,sans-serif';
    for (let i = 0; i <= 4; i++) {{
      const val = maxVal * i / 4;
      const y = padT + plotH * (1 - i/4);
      ctx.fillText(fmtAxis(val), padL - 4, y + 3);
    }}

    // Right Y-axis labels (cumulative %)
    ctx.textAlign = 'left';
    ctx.fillStyle = '#6b7280';
    ctx.font = '10px Segoe UI,sans-serif';
    for (let pct of [25,50,75,100]) {{
      const y = padT + plotH * (1 - pct/100);
      ctx.fillText(pct + '%', padL + plotW + 4, y + 3);
    }}

    // Axes
    ctx.strokeStyle = '#2a2d3e';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + plotH + 1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(padL, padT + plotH); ctx.lineTo(padL + plotW, padT + plotH); ctx.stroke();

    // Bars
    top.forEach((c, i) => {{
      const barH = (c.revenue / maxVal) * plotH;
      const x = padL + i * (barW + gap);
      const y = padT + plotH - barH;

      // Bar fill
      ctx.fillStyle = ragColor(c.gm_pct);
      ctx.fillRect(x, y, barW, barH);

      // Revenue label on top of bar (if bar tall enough)
      if (barH > 20) {{
        ctx.fillStyle = '#e8eaf0';
        ctx.font = 'bold 9px Segoe UI,sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(fmtAxis(c.revenue), x + barW/2, y + 4);
      }}

      // Customer name label (rotated)
      ctx.save();
      ctx.translate(x + barW/2, padT + plotH + 6);
      ctx.rotate(Math.PI / 3.5);
      ctx.fillStyle = '#9096a8';
      ctx.font = '9px Segoe UI,sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(c.name.substring(0, 10), 0, 0);
      ctx.restore();
    }});

    // Cumulative Pareto line (80/20)
    let cumRev = 0;
    const linePoints = [];
    top.forEach((c, i) => {{
      cumRev += c.revenue;
      const pct = cumRev / totalRev;
      const cx = padL + i * (barW + gap) + barW / 2;
      const cy = padT + plotH * (1 - pct);
      linePoints.push([cx, cy, pct]);
    }});

    // Draw cumulative line
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    linePoints.forEach(([cx, cy], i) => {{ if (i===0) ctx.moveTo(cx, cy); else ctx.lineTo(cx, cy); }});
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw 80% reference line
    const y80 = padT + plotH * 0.20;
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(padL, y80); ctx.lineTo(padL + plotW, y80); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#f59e0b';
    ctx.font = '9px Segoe UI,sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('80%', padL + plotW - 2, y80 - 3);

    // Dots on cumulative line
    linePoints.forEach(([cx, cy, pct]) => {{
      ctx.fillStyle = pct <= 0.8 ? '#60a5fa' : '#94a3b8';
      ctx.beginPath(); ctx.arc(cx, cy, 3, 0, Math.PI*2); ctx.fill();
    }});
  }});
}}

function drawQuadrant(filtered) {{
  drawChart('quadrantChart', (ctx, w, h) => {{
    if (!filtered.length) return;

    const padL = 44, padR = 12, padT = 16, padB = 28;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    const plotL = padL;
    const plotT = padT;

    const maxRev = Math.max(...filtered.map(c => c.revenue));
    const medRev  = filtered.map(c => c.revenue).sort((a,b) => a-b)[Math.floor(filtered.length/2)];
    const allMom  = filtered.map(c => c.mom);
    const minMom  = Math.min(...allMom, -30);
    const maxMom  = Math.max(...allMom, 30);

    // Quadrant divider positions
    const xLine = plotL + (medRev / maxRev) * plotW;
    const yZero = maxMom === minMom ? plotT + plotH/2 : plotT + plotH * (1 - (0 - minMom)/(maxMom - minMom));

    // Quadrant background fills
    const quadrants = [
      {{ x: xLine,  y: plotT,   w: plotL+plotW-xLine, h: yZero-plotT,       fill: 'rgba(251,191,36,0.05)',  label: '⭐ Stars',     lx: xLine+6,  ly: plotT+14,  color: '#fbbf24' }},
      {{ x: plotL,  y: plotT,   w: xLine-plotL,       h: yZero-plotT,       fill: 'rgba(96,165,250,0.05)',  label: '🚀 Emerging',  lx: plotL+6,  ly: plotT+14,  color: '#60a5fa' }},
      {{ x: xLine,  y: yZero,   w: plotL+plotW-xLine, h: plotT+plotH-yZero, fill: 'rgba(239,68,68,0.05)',   label: '⚠ At-Risk',   lx: xLine+6,  ly: yZero+14,  color: '#ef4444' }},
      {{ x: plotL,  y: yZero,   w: xLine-plotL,       h: plotT+plotH-yZero, fill: 'rgba(107,114,128,0.05)', label: '🔴 Declining', lx: plotL+6,  ly: yZero+14,  color: '#9ca3af' }},
    ];
    quadrants.forEach(q => {{
      ctx.fillStyle = q.fill;
      ctx.fillRect(q.x, q.y, q.w, q.h);
      ctx.fillStyle = q.color;
      ctx.font = '9px Segoe UI,sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(q.label, q.lx, q.ly);
    }});

    // Divider lines
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(xLine, plotT); ctx.lineTo(xLine, plotT+plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(plotL, yZero); ctx.lineTo(plotL+plotW, yZero); ctx.stroke();
    ctx.setLineDash([]);

    // Axes
    ctx.strokeStyle = '#2a2d3e';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(plotL, plotT); ctx.lineTo(plotL, plotT+plotH); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(plotL, plotT+plotH); ctx.lineTo(plotL+plotW, plotT+plotH); ctx.stroke();

    // Y-axis labels
    ctx.fillStyle = '#9096a8';
    ctx.font = '9px Segoe UI,sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {{
      const val = minMom + (maxMom - minMom) * i / 4;
      const y = plotT + plotH * (1 - i/4);
      ctx.fillText((val > 0 ? '+' : '') + val.toFixed(0) + '%', plotL - 3, y + 3);
    }}

    // X-axis label
    ctx.fillStyle = '#9096a8';
    ctx.font = '10px Segoe UI,sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Revenue →', plotL + plotW/2, plotT + plotH + 18);

    // Bubbles
    const maxR = 18;
    const maxU  = Math.max(...filtered.map(c => c.units || 1));
    filtered.forEach(c => {{
      const cx = plotL + (c.revenue / maxRev) * plotW;
      const cy = maxMom === minMom ? plotT + plotH/2 : plotT + plotH * (1 - (c.mom - minMom)/(maxMom - minMom));
      const r  = Math.max(4, maxR * Math.sqrt(c.units / maxU));

      let bubbleColor = '#9ca3af';
      if (c.revenue >= medRev && c.mom >= 0) bubbleColor = '#fbbf24';
      else if (c.revenue >= medRev && c.mom < 0) bubbleColor = '#ef4444';
      else if (c.revenue < medRev && c.mom >= 0) bubbleColor = '#60a5fa';

      ctx.globalAlpha = 0.75;
      ctx.fillStyle = bubbleColor;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = '#1a1d2e';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.stroke();

      // Name label (for larger bubbles)
      if (r >= 6) {{
        ctx.fillStyle = '#e8eaf0';
        ctx.font = 'bold 8px Segoe UI,sans-serif';
        ctx.textAlign = 'center';
        const label = c.name.substring(0, 5);
        ctx.fillText(label, cx, cy + 3);
      }}
    }});
  }});
}}

function drawMix(filtered) {{
  drawChart('mixChart', (ctx, w, h) => {{
    if (!filtered.length) return;

    const top = [...filtered].sort((a,b) => b.units - a.units).slice(0, 12);
    const legendH = 22;
    const padT = 12, padB = legendH + 10;
    const barAreaH = h - padT - padB;
    const barH = Math.max(14, Math.floor(barAreaH / top.length) - 3);
    const gap = Math.max(2, Math.floor(barAreaH / top.length) - barH);
    const labelW = 100;
    const plotL = labelW + 4;
    const plotW = w - plotL - 12;

    const productOrder = ['chocolate', 'vanilla', 'mango', 'pistachio', 'dream_cake', 'magadat'];

    // Background axis line
    ctx.strokeStyle = '#2a2d3e';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(plotL, padT); ctx.lineTo(plotL, padT + barAreaH); ctx.stroke();

    // Bars with product stacking (products is a dict {{prod: units}})
    top.forEach((c, i) => {{
      const y = padT + i * (barH + gap);
      let x = plotL;
      const prods = c.products || {{}};
      const totalUnits = c.units || 1;

      productOrder.forEach(prod => {{
        const units = prods[prod] || 0;
        if (!units) return;
        const segW = (units / totalUnits) * plotW;
        const color = RAW.productColors[prod] || '#6b7280';

        ctx.fillStyle = color;
        // Rounded end on last segment
        ctx.fillRect(x, y, segW, barH);
        x += segW;
      }});

      // Unit count at end of bar
      ctx.fillStyle = '#6b7280';
      ctx.font = '9px Segoe UI,sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(c.units.toLocaleString(), x + 3, y + barH/2 + 3);

      // Customer label (right-aligned in label column)
      ctx.fillStyle = '#9096a8';
      ctx.font = '9px Segoe UI,sans-serif';
      ctx.textAlign = 'right';
      const label = c.name.length > 12 ? c.name.substring(0, 11) + '…' : c.name;
      ctx.fillText(label, plotL - 6, y + barH/2 + 3);
    }});

    // Legend row
    const legendY = h - legendH + 4;
    let lx = plotL;
    productOrder.forEach(prod => {{
      const color = RAW.productColors[prod] || '#6b7280';
      const label = RAW.productHeb[prod] || prod;
      ctx.fillStyle = color;
      ctx.fillRect(lx, legendY, 8, 8);
      ctx.fillStyle = '#9096a8';
      ctx.font = '9px Segoe UI,sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(label, lx + 11, legendY + 7);
      lx += ctx.measureText(label).width + 22;
    }});
  }});
}}

function drawTrend(filtered) {{
  drawChart('trendChart', (ctx, w, h) => {{
    const trend = RAW.portfolioTrend || [];
    if (!trend.length) return;
    
    const pad = 40;
    const plotW = w - pad * 2;
    const plotH = h - pad * 2;
    const plotL = pad;
    const plotT = pad;
    
    // Determine mode
    const dataKey = TREND_MODE === 'units' ? 'units' : 'revenue';
    const maxVal = Math.max(...trend.map(t => t[dataKey] || 0));
    
    // Draw grid
    ctx.strokeStyle = '#2a2d3e';
    ctx.lineWidth = 1;
    for (let i = 1; i < 5; i++) {{
      const y = plotT + (plotH * i / 5);
      ctx.beginPath();
      ctx.moveTo(plotL, y);
      ctx.lineTo(plotL + plotW, y);
      ctx.stroke();
    }}
    
    // Axes
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(plotL, plotT);
    ctx.lineTo(plotL, plotT + plotH);
    ctx.lineTo(plotL + plotW, plotT + plotH);
    ctx.stroke();
    
    // Plot area
    ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
    ctx.beginPath();
    trend.forEach((t, i) => {{
      const val = t[dataKey] || 0;
      const x = plotL + (i / (trend.length - 1)) * plotW;
      const y = plotT + plotH * (1 - val / maxVal);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }});
    ctx.lineTo(plotL + plotW, plotT + plotH);
    ctx.lineTo(plotL, plotT + plotH);
    ctx.closePath();
    ctx.fill();
    
    // Line
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    trend.forEach((t, i) => {{
      const val = t[dataKey] || 0;
      const x = plotL + (i / (trend.length - 1)) * plotW;
      const y = plotT + plotH * (1 - val / maxVal);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }});
    ctx.stroke();
    
    // Y-axis labels
    for (let i = 0; i <= 4; i++) {{
      const val = maxVal * i / 4;
      const y = plotT + plotH * (1 - i/4);
      canvasText(ctx, fmtAxis(val), plotL - 5, y - 5, {{align: 'right', fontSize: 10, color: '#9096a8'}});
    }}
    
    // X-axis labels and data point dots
    trend.forEach((t, i) => {{
      const val = t[dataKey] || 0;
      const x = plotL + (i / Math.max(trend.length - 1, 1)) * plotW;
      const y = plotT + plotH * (1 - val / maxVal);

      // Data point dot
      ctx.fillStyle = '#3b82f6';
      ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI*2); ctx.fill();
      ctx.strokeStyle = '#1a1d2e';
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI*2); ctx.stroke();

      // Value label above dot
      ctx.fillStyle = '#e8eaf0';
      ctx.font = 'bold 10px Segoe UI,sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(fmtAxis(val), x, y - 10);

      // Month label below axis
      ctx.fillStyle = '#9096a8';
      ctx.font = '10px Segoe UI,sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(t.month || '', x, plotT + plotH + 12);
    }});
  }});
}}

// ── Filtering ──────────────────────────────────────────────────────────────
function getFiltered() {{
  let filtered = RAW.customers.map(c => ({{
    ...c,
    _rev: c.revenue,
    _units: c.units,
    _op: c.op_profit,
    _revScale: 1,
  }}));

  // Apply filters
  if (DIST_FILTER !== '__all__') {{
    filtered = filtered.filter(c => c.dist === DIST_FILTER);
  }}

  if (CUST_FILTER !== '__all__') {{
    filtered = filtered.filter(c => c.name === CUST_FILTER);
  }}

  if (MONTH_FILTER !== '__all__') {{
    filtered = filtered.filter(c => c.months[MONTH_FILTER] && c.months[MONTH_FILTER].revenue > 0);
  }}

  if (STATUS_FILTER !== '__all__') {{
    const momThresholds = {{ active: 0, growing: 10, declining: -1000 }};
    const threshold = momThresholds[STATUS_FILTER];
    if (STATUS_FILTER === 'declining') {{
      filtered = filtered.filter(c => c.mom < 0);
    }} else {{
      filtered = filtered.filter(c => c.mom >= threshold);
    }}
  }}

  return filtered;
}}

function updateAll() {{
  const filtered = getFiltered();
  updateBanner(filtered);
  updateKPIs(filtered);
  drawPareto(filtered);
  drawQuadrant(filtered);
  drawMix(filtered);
  drawTrend(filtered);
  updateTable(filtered);
}}

// ── Banner ────────────────────────────────────────────────────────────────
function updateBanner(filtered) {{
  const iceDist = filtered.filter(c => c.dist === 'icedream').length;
  const mayDist = filtered.filter(c => c.dist === 'mayyan').length;
  document.getElementById('banner-text').innerHTML = 
    `<b>Sales data loaded</b> — Dec '25, Jan '26, Feb '26 (MTD) · November excluded &middot; <b>${{filtered.length}}</b> customers &middot; 2 distributors &middot; Brand filter: <b>Turbo</b> (ice cream) + <b>Dani's</b> (dream cake) · Price DB: 24/2`;
}}

// ── KPIs ──────────────────────────────────────────────────────────────────
function updateKPIs(filtered) {{
  let janRev = 0, janU = 0, janGP = 0, janOP = 0, janCust = 0;
  filtered.forEach(c => {{
    const m = c.months["Jan '26"];
    if (m && m.revenue > 0) {{
      janRev  += m.revenue * c._revScale;
      janU    += m.units   * c._revScale;
      janCust++;
    }}
    janGP += c.gross_profit * c._revScale;
    janOP += c.op_profit    * c._revScale;
  }});
  const totalF = filtered.length;

  // Dec→Jan MoM for portfolio
  const portfolioTrend = RAW.portfolioTrend;
  let mom = 0;
  if (portfolioTrend.length >= 2) {{
    const c = portfolioTrend[1].revenue, p = portfolioTrend[0].revenue;
    mom = p ? (c-p)/p*100 : 0;
  }}
  const momCls   = mom >= 0 ? 'pos' : 'neg';
  const momSign  = mom >= 0 ? '+' : '';

  document.getElementById('kpi-rev').textContent      = '₪' + fmt(janRev);
  document.getElementById('kpi-rev-sub').innerHTML    = `<span class="${{momCls}}">${{momSign}}${{mom.toFixed(1)}}% vs prev month</span>`;
  document.getElementById('kpi-units').textContent    = fmtN(Math.round(janU));
  document.getElementById('kpi-units-sub').textContent= janCust + ' customers w/ sales';
  document.getElementById('kpi-gp').textContent       = '₪' + fmt(janGP);
  const gpPct = janRev > 0 ? (janGP/janRev*100) : 0;
  document.getElementById('kpi-gp-sub').textContent   = 'Avg Gross: ' + gpPct.toFixed(1) + '%';
  document.getElementById('kpi-op').textContent       = '₪' + fmt(janOP);
  document.getElementById('kpi-cust').textContent     = janCust;
  document.getElementById('kpi-cust-sub').textContent = 'of ' + totalF + ' in filter';
  document.getElementById('kpi-mom').textContent      = momSign + mom.toFixed(1) + '%';
  document.getElementById('kpi-mom').className        = 'val ' + (mom >= 0 ? 'green' : 'red');
}}

// ── Table ──────────────────────────────────────────────────────────────
function updateTable(filtered) {{
  const sorted = [...filtered].sort((a, b) => {{
    let aVal = a[SORT_KEY];
    let bVal = b[SORT_KEY];
    if (typeof aVal === 'string') {{
      return SORT_DIR * aVal.localeCompare(bVal, 'he');
    }}
    return SORT_DIR * (aVal - bVal);
  }});

  const tbody = document.getElementById('custTbody');
  const distLabel = {{ icedream: "Icedream", mayyan: "Ma'ayan" }};
  
  if (!sorted.length) {{
    tbody.innerHTML = '<tr><td class="ts" colspan="7">No customers match filter</td></tr>';
    return;
  }}

  tbody.innerHTML = sorted.map(c => `
    <tr onclick="selectCustomer('${{c.name.replace(/'/g, "\'")}}')" style="cursor:pointer">
      <td>${{c.name}}</td>
      <td style="color:#9096a8">${{distLabel[c.dist] || c.dist}}</td>
      <td>₪${{fmt(c.revenue)}}</td>
      <td class="${{rag(c.gm_pct)}}">${{c.gm_pct.toFixed(1)}}%</td>
      <td>₪${{fmt(c.op_profit)}}</td>
      <td>${{fmtN(c.units)}}</td>
      <td class="${{c.mom >= 0 ? 'mom-pos' : 'mom-neg'}}">${{c.mom >= 0 ? '+' : ''}}${{c.mom}}%</td>
    </tr>`).join('');
}}

// ── Filter Controls ────────────────────────────────────────────────────
function applyFilters() {{
  DIST_FILTER   = document.getElementById('sel-dist').value;
  CUST_FILTER   = document.getElementById('sel-customer').value;
  MONTH_FILTER  = document.getElementById('sel-month').value;
  STATUS_FILTER = document.getElementById('sel-status').value;
  updateAll();
}}

function setBrand(b) {{
  BRAND_FILTER = b;
  ['ab', 'turbo', 'danis'].forEach(id => document.getElementById('btn-' + id).classList.toggle('active', id === b));
  updateAll();
}}

function resetFilters() {{
  DIST_FILTER = CUST_FILTER = MONTH_FILTER = STATUS_FILTER = '__all__';
  BRAND_FILTER = 'ab';
  ['ab', 'turbo', 'danis'].forEach(id => document.getElementById('btn-' + id).classList.toggle('active', id === 'ab'));
  document.getElementById('sel-dist').value = '__all__';
  document.getElementById('sel-customer').value = '__all__';
  document.getElementById('sel-month').value = '__all__';
  document.getElementById('sel-status').value = '__all__';
  updateAll();
}}

function selectCustomer(name) {{
  document.getElementById('sel-customer').value = name;
  CUST_FILTER = name;
  applyFilters();
}}

function sortTable(key) {{
  if (SORT_KEY === key) SORT_DIR *= -1; else {{ SORT_KEY = key; SORT_DIR = -1; }}
  updateTable(getFiltered());
}}

// ── Populate Dropdowns ──────────────────────────────────────────────────
function populateCustomers() {{
  const sel = document.getElementById('sel-customer');
  const sorted = [...RAW.customers].sort((a, b) => a.name.localeCompare(b.name, 'he'));
  sorted.forEach(c => {{
    const opt = document.createElement('option');
    opt.value = c.name;
    opt.textContent = c.name;
    sel.appendChild(opt);
  }});
}}

// ── Initialize ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {{
  populateCustomers();
  updateAll();
}});
</script>

</body>
</html>"""



    out = OUTPUT_DIR / 'trade_and_sales_dashboard.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Trade & Sales Dashboard saved: {out}")
    return out


if __name__ == '__main__':
    print("Loading data...")
    raw = consolidate_data()
    print("Building dashboard...")
    build_dashboard(raw)
    print("Done!")
