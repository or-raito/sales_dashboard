#!/usr/bin/env python3
"""
Raito Business Overview — HTML Dashboard Generator
Generates a fully static HTML dashboard with month + brand filters.
"""

from datetime import datetime
from config import (
    fmt as _fmt, fc as _fc, compute_kpis as _compute_kpis, count_pos as _count_pos,
    PRODUCT_NAMES, PRODUCT_SHORT, PRODUCT_STATUS, PRODUCT_COLORS,
    FLAVOR_COLORS, PRODUCTS_ORDER, SELLING_PRICE_B2B, PRODUCTION_COST,
    MONTH_NAMES_HEB, MONTH_ORDER, CHART_MONTHS,
    BRAND_FILTERS, TARGET_MONTHS_STOCK, PALLET_DIVISOR,
    CREATORS, DISTRIBUTOR_NAMES,
    OUTPUT_DIR, pallets,
)



def _bar_html(items, max_val, color='#3b82f6', height=22):
    """Generate CSS bar chart rows."""
    rows = []
    for label, value in items:
        pct = (value / max_val * 100) if max_val > 0 else 0
        rows.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            f'<div style="min-width:100px;text-align:right;font-size:12px">{label}</div>'
            f'<div style="flex:1;background:#f0f0f0;border-radius:4px;height:{height}px">'
            f'<div style="width:{pct:.1f}%;background:{color};height:100%;border-radius:4px;min-width:2px"></div>'
            f'</div>'
            f'<div style="min-width:60px;text-align:left;font-size:12px;font-weight:600">{_fmt(value)}</div>'
            f'</div>'
        )
    return '\n'.join(rows)




def _build_svg_timeline_chart(data, active_products, value_key, title, line_color, fill_id, label_color, fmt_func):
    """Build SVG line chart over 12-month timeline (Oct 2025 - Sep 2026).
    value_key: 'total_value' for revenue, 'units' for quantity.
    """
    # Build data for all 12 months - None where no data
    timeline = []
    for month in CHART_MONTHS:
        md = data['monthly_data'].get(month, {})
        if md:
            val = sum(md.get('combined', {}).get(p, {}).get(value_key, 0) for p in active_products)
            timeline.append((month, val if val > 0 else None))
        else:
            timeline.append((month, None))

    # Chart dimensions
    w, h_chart = 680, 160
    mx_l, mx_r, my_t = 65, 15, 35
    pw = w - mx_l - mx_r
    ph = h_chart - my_t - 10
    h_total = h_chart + 62
    n = len(CHART_MONTHS)  # always 12
    step = pw / (n - 1)

    # X positions for all 12 months
    x_positions = [mx_l + i * step for i in range(n)]

    # Max value for Y scale (from actual data only)
    actual_vals = [v for _, v in timeline if v is not None]
    max_val = max(actual_vals) if actual_vals else 1
    if max_val == 0:
        max_val = 1

    # Compute Y for data points
    data_points = []  # (x, y, month, val) for months with data
    for i, (month, val) in enumerate(timeline):
        if val is not None:
            x = x_positions[i]
            y = my_t + ph - (val / max_val * ph * 0.85)
            data_points.append((x, y, month, val))

    svg = [f'<svg viewBox="0 0 {w} {h_total}" xmlns="http://www.w3.org/2000/svg" style="width:100%;direction:ltr">']

    # Background
    svg.append(f'<rect x="{mx_l}" y="{my_t}" width="{pw}" height="{ph}" fill="#fafbfc" rx="4"/>')

    # Grid lines
    for i in range(5):
        gy = my_t + ph * i / 4
        val = max_val * (4 - i) / 4
        svg.append(f'<line x1="{mx_l}" y1="{gy:.1f}" x2="{mx_l+pw}" y2="{gy:.1f}" stroke="#e5e7eb" stroke-width="0.5"/>')
        svg.append(f'<text x="{mx_l-5}" y="{gy+3:.1f}" text-anchor="end" font-size="7" fill="#aaa">{fmt_func(val)}</text>')

    # Vertical dashed lines for each month
    for i in range(n):
        x = x_positions[i]
        svg.append(f'<line x1="{x:.1f}" y1="{my_t}" x2="{x:.1f}" y2="{my_t+ph}" stroke="#eee" stroke-width="0.5" stroke-dasharray="3,3"/>')

    # Area fill under line (only between data points)
    if len(data_points) >= 2:
        poly_pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y, _, _ in data_points)
        area_pts = poly_pts + f' {data_points[-1][0]:.1f},{my_t+ph:.1f} {data_points[0][0]:.1f},{my_t+ph:.1f}'
        svg.append(f'<defs><linearGradient id="{fill_id}" x1="0" y1="0" x2="0" y2="1">'
                   f'<stop offset="0%" stop-color="{line_color}" stop-opacity="0.18"/>'
                   f'<stop offset="100%" stop-color="{line_color}" stop-opacity="0.02"/>'
                   f'</linearGradient></defs>')
        svg.append(f'<polygon points="{area_pts}" fill="url(#{fill_id})"/>')

        # Line connecting data points
        svg.append(f'<polyline points="{poly_pts}" fill="none" stroke="{line_color}" stroke-width="2.5" stroke-linejoin="round"/>')

    # Month labels on X-axis (all 12)
    label_y = h_chart + 6
    for i, month in enumerate(CHART_MONTHS):
        x = x_positions[i]
        mh = MONTH_NAMES_HEB.get(month, month)
        has_data = timeline[i][1] is not None
        font_w = '600' if has_data else '400'
        fill = '#333' if has_data else '#bbb'
        svg.append(f'<text x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle" font-size="7" font-weight="{font_w}" fill="{fill}">{mh}</text>')

    # Data points: circles + value labels
    for x, y, month, val in data_points:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#fff" stroke="{line_color}" stroke-width="2"/>')
        svg.append(f'<text x="{x:.1f}" y="{y-9:.1f}" text-anchor="middle" font-size="8" font-weight="700" fill="{label_color}">{fmt_func(val)}</text>')

    # % change bars - placed directly under the X-axis label of the LATER month
    bar_y = h_chart + 14
    for i in range(1, len(data_points)):
        prev_val = data_points[i - 1][3]
        curr_val = data_points[i][3]
        pct = ((curr_val - prev_val) / prev_val * 100) if prev_val > 0 else 0
        # Position under the current (later) month's X position
        cx = data_points[i][0]
        bar_h = min(abs(pct) / 100 * 30, 16)
        bar_h = max(bar_h, 4)
        color = '#10b981' if pct >= 0 else '#ef4444'
        sign = '+' if pct >= 0 else ''
        svg.append(f'<rect x="{cx-9:.1f}" y="{bar_y:.1f}" width="18" height="{bar_h:.1f}" fill="{color}" rx="2" opacity="0.8"/>')
        svg.append(f'<text x="{cx:.1f}" y="{bar_y+bar_h+9:.1f}" text-anchor="middle" font-size="7" font-weight="700" fill="{color}">{sign}{pct:.0f}%</text>')

    svg.append('</svg>')
    return f'<div class="card full" style="margin-bottom:14px"><h3>{title}</h3>' + '\n'.join(svg) + '</div>'


def _build_svg_revenue_chart(data, month_list, active_products):
    return _build_svg_timeline_chart(data, active_products, 'total_value',
                                     'Monthly Revenue (₪)', '#2563eb', 'ag', '#1e3a5f', _fc)


def _build_svg_units_chart(data, month_list, active_products):
    return _build_svg_timeline_chart(data, active_products, 'units',
                                     'Monthly Sales (units)', '#f59e0b', 'ag2', '#92400e', _fmt)


def _build_inventory_section(data):
    """Build unified inventory section: Warehouse (Karfree) + Distributors."""
    wh = data.get('warehouse', {})
    dist_inv = data.get('dist_inv', {})

    has_warehouse = wh and wh.get('products')
    has_distributors = bool(dist_inv)

    if not has_warehouse and not has_distributors:
        return ''

    prod_order = ['chocolate', 'vanilla', 'mango', 'pistachio', 'magadat', 'dream_cake']
    wh_products = wh.get('products', {}) if has_warehouse else {}

    # ── Karfree warehouse table with production planning columns ──
    karfree_html = ''
    if has_warehouse:
        report_date = wh.get('report_date', 'N/A')
        total_units = wh.get('total_units', 0)
        total_pallets = wh.get('total_pallets', 0)

        months = data.get('months', [])
        num_months = len(months) if months else 1

        rows = ''
        for p in prod_order:
            pd = wh_products.get(p)
            if not pd:
                continue
            name = PRODUCT_NAMES.get(p, p)
            units = pd.get('units', 0)
            plt = pd.get('pallets', 0)
            pct = round(units / total_units * 100) if total_units > 0 else 0

            batches = pd.get('batches', [])
            expiry_dates = [b['expiry'] for b in batches if b.get('expiry')]
            earliest_exp = min(expiry_dates) if expiry_dates else '---'
            latest_exp = max(expiry_dates) if expiry_dates else '---'

            # Production planning columns
            p_total = sum(
                data['monthly_data'].get(m, {}).get('combined', {}).get(p, {}).get('units', 0)
                for m in months)
            avg_monthly = round(p_total / num_months) if num_months > 0 else 0
            last_md = data['monthly_data'].get(months[-1], {}) if months else {}
            last_month_u = last_md.get('combined', {}).get(p, {}).get('units', 0)

            # Coverage calc based on Karfree stock only
            if avg_monthly > 0:
                months_stock = round(units / avg_monthly, 1)
            else:
                months_stock = 99 if units > 0 else 0

            if months_stock >= TARGET_MONTHS_STOCK * 1.5:
                cov_color = '#10b981'; cov_label = 'OK'
            elif months_stock >= TARGET_MONTHS_STOCK * 0.5:
                cov_color = '#f59e0b'; cov_label = 'Low'
            else:
                cov_color = '#ef4444'; cov_label = 'Critical'

            target_units = avg_monthly * TARGET_MONTHS_STOCK
            suggested = max(0, target_units - units)
            bar_pct = min(months_stock / 3 * 100, 100)

            sug_pallets = '-' if p == 'dream_cake' else (str(round(suggested / PALLET_DIVISOR, 1)) if suggested > 0 else '✓')

            rows += (f'<tr>'
                     f'<td><b>{name}</b></td>'
                     f'<td style="text-align:center">{_fmt(units)}</td>'
                     f'<td style="text-align:center">{plt}</td>'
                     f'<td style="text-align:center">{pct}%</td>'
                     f'<td style="text-align:center;font-size:11px">{earliest_exp}</td>'
                     f'<td style="text-align:center;font-size:11px">{latest_exp}</td>'
                     f'<td style="text-align:center">{_fmt(avg_monthly)}</td>'
                     f'<td style="text-align:center">{_fmt(last_month_u)}</td>'
                     f'<td style="text-align:center">'
                     f'<div style="display:flex;align-items:center;gap:4px;justify-content:center">'
                     f'<div style="width:60px;background:#f0f0f0;border-radius:3px;height:14px">'
                     f'<div style="width:{bar_pct:.0f}%;background:{cov_color};height:100%;border-radius:3px"></div></div>'
                     f'<span style="font-weight:700;color:{cov_color}">{months_stock}</span></div></td>'
                     f'<td style="text-align:center;font-weight:700;color:{cov_color}">{cov_label}</td>'
                     f'<td style="text-align:center;font-weight:700">{_fmt(suggested) if suggested > 0 else "✓"}</td>'
                     f'<td style="text-align:center;color:#888;font-size:12px">{sug_pallets}</td>'
                     f'</tr>')

        rows += (f'<tr style="font-weight:700;border-top:2px solid #1e3a5f">'
                 f'<td>Total</td>'
                 f'<td style="text-align:center">{_fmt(total_units)}</td>'
                 f'<td style="text-align:center">{total_pallets}</td>'
                 f'<td style="text-align:center">100%</td>'
                 f'<td></td><td></td>'
                 f'<td></td><td></td><td></td><td></td><td></td><td></td></tr>')

        bars = ''
        colors = {'chocolate': '#8B4513', 'vanilla': '#F5DEB3', 'mango': '#FF8C00',
                  'pistachio': '#93C572', 'dream_cake': '#DB7093'}
        for p in prod_order:
            pd = wh_products.get(p)
            if not pd:
                continue
            units = pd.get('units', 0)
            pct = round(units / total_units * 100) if total_units > 0 else 0
            color = colors.get(p, '#6366f1')
            name = PRODUCT_SHORT.get(p, p)
            bars += (f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
                     f'<div style="min-width:80px;text-align:right;font-size:12px">{name}</div>'
                     f'<div style="flex:1;background:#f0f0f0;border-radius:4px;height:22px">'
                     f'<div style="width:{pct}%;background:{color};height:100%;border-radius:4px;min-width:2px"></div></div>'
                     f'<div style="min-width:90px;font-size:12px;font-weight:600">{_fmt(units)} ({pct}%)</div></div>')

        karfree_html = (f'<div class="card full" style="margin-bottom:14px">'
                   f'<h3>Transfer Warehouse Inventory (Karfree) — as of {report_date}</h3>'
                   f'{bars}'
                   f'<table class="tbl" style="margin-top:12px"><thead><tr>'
                   f'<th>Product</th><th>Units in Stock</th><th>Pallets</th>'
                   f'<th>Share</th><th>Earliest Expiry</th><th>Latest Expiry</th>'
                   f'<th>Avg Sales/Mo</th><th>Last Month</th>'
                   f'<th>Months of Stock</th><th>Status</th>'
                   f'<th>Suggested Production</th><th style="color:#888;font-size:11px">Pallets</th>'
                   f'</tr></thead><tbody>{rows}</tbody></table></div>')

    # ── Distributor inventory tables ──
    dist_html = ''
    if has_distributors:
        for dist_key, dist_label in [('icedream', 'Icedream'), ('mayyan', "Ma'ayan")]:
            ddata = dist_inv.get(dist_key)
            if not ddata or not ddata.get('products'):
                continue
            d_date = ddata.get('report_date', 'N/A')
            d_total = ddata.get('total_units', 0)
            d_prods = ddata['products']

            d_rows = ''
            d_pallets_total = 0
            for p in prod_order:
                pd = d_prods.get(p)
                if not pd:
                    continue
                name = PRODUCT_NAMES.get(p, p)
                units = pd.get('units', 0)
                pct = round(units / d_total * 100) if d_total > 0 else 0
                plt_str = '-' if p == 'dream_cake' else str(round(units / 2400, 1))
                if p != 'dream_cake':
                    d_pallets_total += round(units / 2400, 1)
                d_rows += (f'<tr>'
                           f'<td><b>{name}</b></td>'
                           f'<td style="text-align:center">{_fmt(units)}</td>'
                           f'<td style="text-align:center;color:#888;font-size:12px">{plt_str}</td>'
                           f'<td style="text-align:center">{pct}%</td>'
                           f'</tr>')
            d_rows += (f'<tr style="font-weight:700;border-top:2px solid #1e3a5f">'
                       f'<td>Total</td>'
                       f'<td style="text-align:center">{_fmt(d_total)}</td>'
                       f'<td style="text-align:center;color:#888;font-size:12px">{d_pallets_total}</td>'
                       f'<td style="text-align:center">100%</td></tr>')

            dist_html += (f'<div class="card half" style="margin-bottom:14px">'
                          f'<h3>Distributor Inventory ({dist_label}) — as of {d_date}</h3>'
                          f'<table class="tbl"><thead><tr>'
                          f'<th>Product</th><th>Units</th><th style="color:#888;font-size:11px">Pallets</th><th>Share</th>'
                          f'</tr></thead><tbody>{d_rows}</tbody></table></div>')

    # ── Unified total stock summary with pallets ──
    summary_html = ''
    if has_warehouse or has_distributors:
        def _pallets_str(units, product):
            """Ice cream pallets = floor(units/2400). Dream cake = '-'."""
            if product == 'dream_cake':
                return '-'
            return str(round(units / 2400, 1)) if units > 0 else '-'

        s_rows = ''
        grand_total = 0
        grand_pallets = 0
        for p in prod_order:
            wh_u = wh_products.get(p, {}).get('units', 0)
            ice_u = dist_inv.get('icedream', {}).get('products', {}).get(p, {}).get('units', 0)
            may_u = dist_inv.get('mayyan', {}).get('products', {}).get(p, {}).get('units', 0)
            total_u = wh_u + ice_u + may_u
            if total_u == 0:
                continue
            name = PRODUCT_NAMES.get(p, p)
            color = FLAVOR_COLORS.get(p, '#666')
            dot = f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:6px"></span>'

            wh_p = _pallets_str(wh_u, p)
            ice_p = _pallets_str(ice_u, p)
            may_p = _pallets_str(may_u, p)
            total_p = _pallets_str(total_u, p)
            if p != 'dream_cake':
                grand_pallets += round(total_u / 2400, 1)

            s_rows += (f'<tr>'
                       f'<td>{dot}<b>{name}</b></td>'
                       f'<td style="text-align:center">{_fmt(wh_u) if wh_u else "-"}</td>'
                       f'<td style="text-align:center;color:#888;font-size:12px">{wh_p}</td>'
                       f'<td style="text-align:center">{_fmt(ice_u) if ice_u else "-"}</td>'
                       f'<td style="text-align:center;color:#888;font-size:12px">{ice_p}</td>'
                       f'<td style="text-align:center">{_fmt(may_u) if may_u else "-"}</td>'
                       f'<td style="text-align:center;color:#888;font-size:12px">{may_p}</td>'
                       f'<td style="text-align:center;font-weight:700">{_fmt(total_u)}</td>'
                       f'<td style="text-align:center;font-weight:700;color:#555">{total_p}</td>'
                       f'</tr>')
            grand_total += total_u

        wh_total = wh.get('total_units', 0) if has_warehouse else 0
        ice_total = dist_inv.get('icedream', {}).get('total_units', 0)
        may_total = dist_inv.get('mayyan', {}).get('total_units', 0)
        s_rows += (f'<tr style="font-weight:700;border-top:2px solid #1e3a5f">'
                   f'<td>Total</td>'
                   f'<td style="text-align:center">{_fmt(wh_total) if wh_total else "-"}</td>'
                   f'<td style="text-align:center;color:#888;font-size:12px">{round(wh_total / 2400, 1) if wh_total else "-"}</td>'
                   f'<td style="text-align:center">{_fmt(ice_total) if ice_total else "-"}</td>'
                   f'<td style="text-align:center;color:#888;font-size:12px">{round(ice_total / 2400, 1) if ice_total else "-"}</td>'
                   f'<td style="text-align:center">{_fmt(may_total) if may_total else "-"}</td>'
                   f'<td style="text-align:center;color:#888;font-size:12px">{round(may_total / 2400, 1) if may_total else "-"}</td>'
                   f'<td style="text-align:center;font-weight:700">{_fmt(grand_total)}</td>'
                   f'<td style="text-align:center;font-weight:700;color:#555">{grand_pallets}</td>'
                   f'</tr>')

        summary_html = (f'<div class="card full" style="margin-bottom:14px">'
                        f'<h3>Total Available Stock — All Locations</h3>'
                        f'<table class="tbl"><thead><tr>'
                        f'<th>Product</th>'
                        f'<th>Warehouse (Karfree)</th><th style="color:#888;font-size:11px">Pallets</th>'
                        f'<th>Icedream</th><th style="color:#888;font-size:11px">Pallets</th>'
                        f'<th>Ma\'ayan</th><th style="color:#888;font-size:11px">Pallets</th>'
                        f'<th>Total Available</th><th style="color:#888;font-size:11px">Pallets</th>'
                        f'</tr></thead><tbody>{s_rows}</tbody></table></div>')

    # Wrap distributor cards in a flex row
    if dist_html:
        dist_html = f'<div style="display:flex;gap:14px;flex-wrap:wrap">{dist_html}</div>'

    return summary_html + karfree_html + dist_html


FLAVOR_COLORS = {
    'chocolate': '#8B4513', 'vanilla': '#DAA520', 'mango': '#FF8C00',
    'pistachio': '#93C572', 'dream_cake': '#DB7093', 'magadat': '#9CA3AF',
}
TARGET_MONTHS_STOCK = 1  # Target months of inventory to maintain

def _build_flavor_svg_chart(data, months):
    """Build SVG multi-line chart showing units per flavor over 12-month timeline."""
    products_order = ['chocolate', 'vanilla', 'mango', 'dream_cake', 'magadat']
    w, h_chart = 680, 180
    pad_l, pad_r, pad_t = 65, 20, 10

    # Collect data per product per month
    all_vals = []
    product_lines = {}
    for p in products_order:
        line = []
        for month in CHART_MONTHS:
            md = data['monthly_data'].get(month, {})
            u = md.get('combined', {}).get(p, {}).get('units', 0)
            line.append(u if u > 0 else None)
            if u > 0:
                all_vals.append(u)
        product_lines[p] = line

    if not all_vals:
        return ''

    max_val = 50000  # Fixed Y-axis ceiling for consistent scale
    min_val = 0
    x_start = pad_l
    x_end = w - pad_r
    step_x = (x_end - x_start) / (len(CHART_MONTHS) - 1)
    x_positions = [x_start + i * step_x for i in range(len(CHART_MONTHS))]

    def y_pos(val):
        if max_val == min_val:
            return h_chart / 2 + pad_t
        clamped = min(val, max_val)
        return pad_t + (1 - (clamped - min_val) / (max_val - min_val)) * (h_chart - 20)

    svg = [f'<svg viewBox="0 0 {w} {h_chart + 40}" style="width:100%;font-family:system-ui,sans-serif">']

    # Y-axis grid
    for i in range(5):
        yv = min_val + (max_val - min_val) * (4 - i) / 4
        yp = y_pos(yv)
        svg.append(f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{w-pad_r}" y2="{yp:.1f}" stroke="#eee" stroke-width="1"/>')
        svg.append(f'<text x="{pad_l-5}" y="{yp+3:.1f}" text-anchor="end" font-size="7" fill="#aaa">{_fmt(yv)}</text>')

    # X-axis month labels
    label_y = h_chart + 6
    for i, month in enumerate(CHART_MONTHS):
        x = x_positions[i]
        mh = MONTH_NAMES_HEB.get(month, month)
        has_data = any(product_lines[p][i] is not None for p in products_order)
        font_w = '600' if has_data else '400'
        fill = '#333' if has_data else '#bbb'
        svg.append(f'<text x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle" font-size="7" font-weight="{font_w}" fill="{fill}">{mh}</text>')

    # Draw lines per product
    for p in products_order:
        line = product_lines[p]
        color = FLAVOR_COLORS.get(p, '#666')
        points = []
        for i, val in enumerate(line):
            if val is not None:
                points.append((x_positions[i], y_pos(val), val))
        if len(points) < 1:
            continue
        # Polyline
        if len(points) >= 2:
            pts_str = ' '.join(f'{x:.1f},{y:.1f}' for x, y, _ in points)
            svg.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" opacity="0.9"/>')
        # Data points + labels
        for x, y, val in points:
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#fff" stroke="{color}" stroke-width="2"/>')
            svg.append(f'<text x="{x:.1f}" y="{y-8:.1f}" text-anchor="middle" font-size="7" font-weight="700" fill="{color}">{_fmt(val)}</text>')

    # Legend
    lx = pad_l
    ly = h_chart + 22
    for p in products_order:
        if not any(v is not None for v in product_lines[p]):
            continue
        color = FLAVOR_COLORS.get(p, '#666')
        name = PRODUCT_SHORT.get(p, p)
        svg.append(f'<rect x="{lx}" y="{ly}" width="10" height="10" rx="2" fill="{color}"/>')
        svg.append(f'<text x="{lx+13}" y="{ly+9}" font-size="8" fill="#333">{name}</text>')
        lx += len(name) * 6 + 24

    svg.append('</svg>')
    return '\n'.join(svg)


def _build_flavor_analysis(data, month_list, is_all):
    """Build units-only sales-by-flavor analysis for production planning.
    Overview: multi-line chart + monthly units table + inventory coverage.
    Per-month: bar chart with units per flavor.
    """
    products_order = ['chocolate', 'vanilla', 'mango', 'pistachio', 'dream_cake', 'magadat']
    wh = data.get('warehouse', {})
    wh_products = wh.get('products', {}) if wh else {}
    dist_inv = data.get('dist_inv', {})

    if is_all:
        months = month_list
        num_months = len(months)

        chart_html = ''  # Removed flavor trend chart per user request

        # ── Monthly units table ──
        month_labels = [MONTH_NAMES_HEB.get(m, m) for m in months]
        hdr = '<th>Product</th>'
        for ml in month_labels:
            hdr += f'<th>{ml}</th>'
        hdr += '<th>Total</th><th>Avg/Month</th><th>Trend</th>'

        rows = ''
        grand_units = 0
        for p in products_order:
            name = PRODUCT_NAMES.get(p, p)
            color = FLAVOR_COLORS.get(p, '#666')
            row = f'<td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:6px"></span><b>{name}</b></td>'
            monthly_units = []
            p_total = 0
            has_data = False
            for month in months:
                md = data['monthly_data'].get(month, {})
                u = md.get('combined', {}).get(p, {}).get('units', 0)
                monthly_units.append(u)
                p_total += u
                if u > 0:
                    has_data = True
                row += f'<td style="text-align:center">{_fmt(u) if u else "-"}</td>'

            avg = round(p_total / num_months) if num_months > 0 else 0
            # Trend: compare last month to first month with data
            non_zero = [u for u in monthly_units if u > 0]
            if len(non_zero) >= 2:
                trend_pct = round((non_zero[-1] - non_zero[-2]) / non_zero[-2] * 100)
                trend_color = '#10b981' if trend_pct >= 0 else '#ef4444'
                trend_sign = '+' if trend_pct >= 0 else ''
                trend_str = f'<span style="color:{trend_color};font-weight:700">{trend_sign}{trend_pct}%</span>'
            else:
                trend_str = '-'

            row += f'<td class="tot" style="text-align:center">{_fmt(p_total)}</td>'
            row += f'<td style="text-align:center;font-weight:600">{_fmt(avg)}</td>'
            row += f'<td style="text-align:center">{trend_str}</td>'
            if has_data:
                rows += f'<tr>{row}</tr>'
                grand_units += p_total

        # Total row
        total_row = '<td><b>Total</b></td>'
        for month in months:
            md = data['monthly_data'].get(month, {})
            mu = sum(md.get('combined', {}).get(p, {}).get('units', 0) for p in products_order)
            total_row += f'<td style="text-align:center"><b>{_fmt(mu)}</b></td>'
        grand_avg = round(grand_units / num_months) if num_months > 0 else 0
        total_row += f'<td class="tot" style="text-align:center"><b>{_fmt(grand_units)}</b></td>'
        total_row += f'<td style="text-align:center"><b>{_fmt(grand_avg)}</b></td>'
        total_row += '<td></td>'
        rows += f'<tr style="border-top:2px solid #1e3a5f">{total_row}</tr>'

        # Share bar
        bar_segments = ''
        x_offset = 0
        total_w = 500
        for p in products_order:
            p_total_u = sum(
                data['monthly_data'].get(m, {}).get('combined', {}).get(p, {}).get('units', 0)
                for m in months)
            if p_total_u == 0 or grand_units == 0:
                continue
            pct = p_total_u / grand_units * 100
            seg_w = pct / 100 * total_w
            color = FLAVOR_COLORS.get(p, '#666')
            rx = '4' if x_offset == 0 else '0'
            bar_segments += f'<rect x="{x_offset:.1f}" y="0" width="{seg_w:.1f}" height="28" fill="{color}" rx="{rx}"/>'
            if pct > 5:
                bar_segments += f'<text x="{x_offset + seg_w/2:.1f}" y="18" text-anchor="middle" font-size="10" fill="white" font-weight="600">{PRODUCT_SHORT.get(p,p)} {pct:.0f}%</text>'
            x_offset += seg_w
        share_bar = (f'<svg viewBox="0 0 {total_w} 28" style="width:100%;max-width:600px;margin:10px auto;display:block">'
                     f'{bar_segments}</svg>')

        units_table = (f'<div class="card full" style="margin-bottom:14px">'
                       f'<h3>Units Sold by Flavor — Monthly</h3>'
                       f'{share_bar}'
                       f'<table class="tbl" style="margin-top:10px"><thead><tr>{hdr}</tr></thead>'
                       f'<tbody>{rows}</tbody></table></div>')

        # ── Inventory Coverage / Production Planning ──
        coverage_html = ''
        has_any_stock = wh_products or dist_inv
        if has_any_stock:
            cov_rows = ''
            for p in products_order:
                name = PRODUCT_NAMES.get(p, p)
                color = FLAVOR_COLORS.get(p, '#666')

                # Avg monthly sales
                p_total = sum(
                    data['monthly_data'].get(m, {}).get('combined', {}).get(p, {}).get('units', 0)
                    for m in months)
                avg_monthly = round(p_total / num_months) if num_months > 0 else 0

                # Last month sales
                last_md = data['monthly_data'].get(months[-1], {})
                last_month_u = last_md.get('combined', {}).get(p, {}).get('units', 0)

                # Current stock — total across all locations
                wh_stock = wh_products.get(p, {}).get('units', 0)
                ice_stock = dist_inv.get('icedream', {}).get('products', {}).get(p, {}).get('units', 0)
                may_stock = dist_inv.get('mayyan', {}).get('products', {}).get(p, {}).get('units', 0)
                stock = wh_stock + ice_stock + may_stock

                # Months of stock remaining (based on avg)
                if avg_monthly > 0:
                    months_stock = round(stock / avg_monthly, 1)
                else:
                    months_stock = 99 if stock > 0 else 0

                # Coverage bar color
                if months_stock >= TARGET_MONTHS_STOCK * 1.5:
                    cov_color = '#10b981'  # green - good
                    cov_label = 'OK'
                elif months_stock >= TARGET_MONTHS_STOCK * 0.5:
                    cov_color = '#f59e0b'  # yellow - warning
                    cov_label = 'Low'
                else:
                    cov_color = '#ef4444'  # red - critical
                    cov_label = 'Critical'

                # Suggested production (to reach target months of stock)
                target_units = avg_monthly * TARGET_MONTHS_STOCK
                suggested = max(0, target_units - stock)

                # Coverage bar visual (max 3 months width)
                bar_pct = min(months_stock / 3 * 100, 100)

                if avg_monthly == 0 and stock == 0:
                    continue

                dot = f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:6px"></span>'
                stock_pallets = '-' if p == 'dream_cake' else str(round(stock / 2400, 1))
                sug_pallets = '-' if p == 'dream_cake' else (str(round(suggested / 2400, 1)) if suggested > 0 else '✓')
                cov_rows += (f'<tr>'
                             f'<td>{dot}<b>{name}</b></td>'
                             f'<td style="text-align:center">{_fmt(avg_monthly)}</td>'
                             f'<td style="text-align:center">{_fmt(last_month_u)}</td>'
                             f'<td style="text-align:center"><b>{_fmt(stock)}</b></td>'
                             f'<td style="text-align:center;color:#888;font-size:12px">{stock_pallets}</td>'
                             f'<td style="text-align:center">'
                             f'<div style="display:flex;align-items:center;gap:4px;justify-content:center">'
                             f'<div style="width:60px;background:#f0f0f0;border-radius:3px;height:14px">'
                             f'<div style="width:{bar_pct:.0f}%;background:{cov_color};height:100%;border-radius:3px"></div></div>'
                             f'<span style="font-weight:700;color:{cov_color}">{months_stock}</span></div></td>'
                             f'<td style="text-align:center;font-weight:700;color:{cov_color}">{cov_label}</td>'
                             f'<td style="text-align:center;font-weight:700">{_fmt(suggested) if suggested > 0 else "✓"}</td>'
                             f'<td style="text-align:center;color:#888;font-size:12px">{sug_pallets}</td>'
                             f'</tr>')

            coverage_html = (f'<div class="card full" style="margin-bottom:14px">'
                             f'<h3>Inventory Coverage & Production Planning (target: {TARGET_MONTHS_STOCK} month stock)</h3>'
                             f'<table class="tbl"><thead><tr>'
                             f'<th>Product</th><th>Avg Sales/Mo</th><th>Last Month</th>'
                             f'<th>Current Stock</th><th style="color:#888;font-size:11px">Pallets</th><th>Months of Stock</th><th>Status</th>'
                             f'<th>Suggested Production</th><th style="color:#888;font-size:11px">Pallets</th>'
                             f'</tr></thead><tbody>{cov_rows}</tbody></table></div>')

        return chart_html + units_table + coverage_html

    else:
        # ── Per-month: single month flavor breakdown with bars (units only) ──
        month = month_list[0]
        md = data['monthly_data'].get(month, {})

        flavor_data = []
        total_u = 0
        for p in products_order:
            c = md.get('combined', {}).get(p, {})
            u = c.get('units', 0)
            if u > 0:
                flavor_data.append((p, u))
                total_u += u

        if not flavor_data:
            return ''

        # Sort by units descending
        flavor_data.sort(key=lambda x: x[1], reverse=True)
        max_u = flavor_data[0][1] if flavor_data else 1

        bars = ''
        for p, u in flavor_data:
            name = PRODUCT_NAMES.get(p, p)
            color = FLAVOR_COLORS.get(p, '#666')
            pct = round(u / total_u * 100) if total_u > 0 else 0
            bar_w = u / max_u * 100 if max_u > 0 else 0
            # Distributor split
            c = md.get('combined', {}).get(p, {})
            may_u = c.get('mayyan_units', 0)
            ice_u = c.get('icedreams_units', 0)
            split_str = ''
            if may_u > 0 and ice_u > 0:
                split_str = f' <span style="font-size:10px;color:#888">(Ma\'ayan {_fmt(may_u)} / Icedream {_fmt(ice_u)})</span>'
            elif may_u > 0:
                split_str = f' <span style="font-size:10px;color:#888">(Ma\'ayan)</span>'
            elif ice_u > 0:
                split_str = f' <span style="font-size:10px;color:#888">(Icedream)</span>'

            bars += (f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0">'
                     f'<div style="min-width:130px;text-align:right;font-size:12px">'
                     f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:4px"></span>{name}</div>'
                     f'<div style="flex:1;background:#f0f0f0;border-radius:4px;height:24px">'
                     f'<div style="width:{bar_w:.1f}%;background:{color};height:100%;border-radius:4px;min-width:2px;opacity:0.85"></div></div>'
                     f'<div style="min-width:180px;font-size:12px"><b>{_fmt(u)}</b> units ({pct}%){split_str}</div></div>')

        # Total line
        bars += (f'<div style="border-top:2px solid #1e3a5f;margin-top:6px;padding-top:6px;display:flex;justify-content:space-between;font-weight:700;font-size:13px">'
                 f'<span>Total</span><span>{_fmt(total_u)} units</span></div>')

        return (f'<div class="card full" style="margin-bottom:14px">'
                f'<h3>Units Sold by Flavor</h3>{bars}</div>')


def _build_month_section(data, month_list, section_id, active_products):
    """Build one month section (KPIs + charts + tables)."""
    products = data['products']
    tu, tr, tc, tgm, tmy, tic, mp, ip = _compute_kpis(data, month_list, active_products)
    is_all = len(month_list) > 1
    label = 'Overview' if is_all else MONTH_NAMES_HEB.get(month_list[0], month_list[0])

    # ── KPI Cards ──
    pos_count = _count_pos(data, month_list)

    # Creators card - filtered by brand
    creators_blocks = ''
    cr_idx = 0
    for cr in CREATORS:
        # Only show creator if they have products in active_products
        relevant_skus = [p for p in cr['products'] if p in active_products]
        if not relevant_skus:
            continue
        sku_count = len(relevant_skus)
        if cr_idx > 0:
            creators_blocks += '<hr style="border:none;border-top:1px solid #e0e0e0;margin:8px 0">'
        creators_blocks += (
            f'<div style="margin:6px 0">'
            f'<div style="font-size:14px;font-weight:600">{cr["name"]} - {cr["brand"]}</div>'
            f'<div style="font-size:13px;color:var(--text2);margin-top:2px">SKU\'s &bull; {sku_count}</div>'
            f'</div>')
        cr_idx += 1

    kf = 'font-size:14px;margin:6px 0'

    sales_card = f'''<div class="kpi">
    <div class="kpi-title">SALES</div>
    <div style="{kf}">Total Revenue - <b style="color:#10b981">{_fc(tr)}</b></div>
    <div style="{kf}">Total Units Sold - <b>{_fmt(tu)}</b></div>
    <div style="{kf}">Total Points of Sale - <b>{pos_count}</b></div>
  </div>'''

    creators_card = f'''<div class="kpi">
    <div class="kpi-title">Creators</div>
    {creators_blocks}
  </div>'''

    # Supply Chain card - show inventory if available
    wh = data.get('warehouse', {})
    inv_total = wh.get('total_units', 0)
    if inv_total > 0:
        inv_display = f'<b style="color:#2563eb">{_fmt(inv_total)}</b> units'
    else:
        inv_display = '<span style="color:#999">---</span>'

    supply_card = f'''<div class="kpi">
    <div class="kpi-title">Supply Chain</div>
    <div style="{kf}">Waste - Total <span style="color:#999">---</span></div>
    <div style="{kf}">Inventory (Warehouse) - {inv_display}</div>
    <div style="{kf}">Production Costs - Total <span style="color:#999">---</span></div>
    <div style="font-size:11px;color:#999;margin-top:6px">{'Awaiting data' if inv_total == 0 else ''}</div>
  </div>'''

    if is_all:
        kpis = f'''<div style="text-align:center;font-size:20px;font-weight:700;color:#1e3a5f;margin-bottom:14px">KPI's</div>
<div class="kpis" style="grid-template-columns:repeat(3,1fr)">
  {sales_card}
  {creators_card}
  {supply_card}
</div>'''
    else:
        dist_card = f'''<div class="kpi">
    <div class="kpi-title">Distribution</div>
    <div style="{kf}">Ma'ayan - <b style="color:#2563eb">{mp}%</b> ({_fmt(tmy)} units)</div>
    <div style="{kf}">Icedream - <b style="color:#2563eb">{ip}%</b> ({_fmt(tic)} units)</div>
  </div>'''

        kpis = f'''<div style="text-align:center;font-size:20px;font-weight:700;color:#1e3a5f;margin-bottom:14px">KPI's</div>
<div class="kpis" style="grid-template-columns:repeat(4,1fr)">
  {sales_card}
  {dist_card}
  {creators_card}
  {supply_card}
</div>'''

    # ── Revenue & Units Charts ──
    units_card = ''
    if is_all and len(month_list) >= 2:
        rev_card = _build_svg_revenue_chart(data, month_list, active_products)
        units_card = _build_svg_units_chart(data, month_list, active_products)
    else:
        rev_bars = ''
        max_r = max(
            (sum(data['monthly_data'][m]['combined'].get(p, {}).get('total_value', 0) for p in active_products)
             for m in month_list), default=1)
        for month in month_list:
            md = data['monthly_data'][month]
            mh = MONTH_NAMES_HEB.get(month, month)
            rev = sum(md['combined'].get(p, {}).get('total_value', 0) for p in active_products)
            rp = rev / max_r * 100 if max_r > 0 else 0
            rev_bars += (f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
                         f'<div style="min-width:90px;text-align:right;font-size:12px">{mh}</div>'
                         f'<div style="flex:1;background:#f0f0f0;border-radius:4px;height:22px">'
                         f'<div style="width:{rp:.1f}%;background:#10b981;height:100%;border-radius:4px;min-width:2px"></div></div>'
                         f'<div style="min-width:80px;font-size:12px;font-weight:600">{_fc(rev)}</div></div>')
        rev_card = f'<div class="card full" style="margin-bottom:14px"><h3>Revenue</h3>{rev_bars}</div>'

    # ── Summary Table (sorted by revenue desc) ──
    rows_data = []
    for month in month_list:
        md = data['monthly_data'][month]
        mh = MONTH_NAMES_HEB.get(month, month)
        for p in active_products:
            c = md['combined'].get(p, {})
            u = c.get('units', 0)
            if u == 0:
                continue
            disc = PRODUCT_STATUS.get(p) == 'discontinued'
            badge = '<span class="badge disc">Disc.</span>' if disc else (
                '<span class="badge new">New</span>' if PRODUCT_STATUS.get(p) == 'new' else '')
            ds = ' style="color:#999;font-style:italic"' if disc else ''
            val = c.get('total_value', 0)
            row_html = (f'<tr{ds}><td><b>{mh}</b></td><td>{PRODUCT_NAMES.get(p,p)} {badge}</td>'
                        f'<td>{_fmt(c.get("mayyan_units",0))}</td><td>{_fmt(c.get("icedreams_units",0))}</td>'
                        f'<td><b>{_fmt(u)}</b></td><td>{_fc(val)}</td></tr>')
            rows_data.append((val, row_html))
    rows_data.sort(key=lambda x: x[0], reverse=True)
    monthly_rows = '\n'.join(r for _, r in rows_data)

    summary_tbl = (f'<div class="card full" style="margin-bottom:14px"><h3>Detailed Summary - {label}</h3>'
                   f'<table class="tbl"><thead><tr><th>Month</th><th>Product</th><th>Ma\'ayan (units)</th>'
                   f'<th>Icedream (units)</th><th>Total Units</th><th>Revenue (₪)</th></tr></thead>'
                   f'<tbody>{monthly_rows}</tbody></table></div>')

    # ── Icedream Customers (aggregated by chain, sorted by revenue desc) ──
    from config import extract_chain_name
    ice_pl = [p for p in ['chocolate', 'vanilla', 'mango', 'pistachio', 'magadat', 'dream_cake'] if p in active_products]
    ice_h = ''.join(f'<th>{PRODUCT_SHORT[p]} (units)</th>' for p in ice_pl)
    ice_h += ''.join(f'<th>{PRODUCT_SHORT[p]} (₪)</th>' for p in ice_pl)
    ice_rows_data = []
    for month in month_list:
        md = data['monthly_data'][month]
        mh = MONTH_NAMES_HEB.get(month, month)
        # Aggregate branches into chains
        chains = {}
        for cust, pdata in md.get('icedreams_customers', {}).items():
            chain = extract_chain_name(cust)
            if chain not in chains:
                chains[chain] = {}
            for p in ice_pl:
                if p not in chains[chain]:
                    chains[chain][p] = {'units': 0, 'value': 0}
                chains[chain][p]['units'] += pdata.get(p, {}).get('units', 0)
                chains[chain][p]['value'] += pdata.get(p, {}).get('value', 0)
        for chain, pdata in chains.items():
            ctu = sum(pdata.get(p, {}).get('units', 0) for p in ice_pl)
            ctv = sum(pdata.get(p, {}).get('value', 0) for p in ice_pl)
            r = f'<td>{mh}</td><td><b>{chain}</b></td>'
            for p in ice_pl:
                u = pdata.get(p, {}).get('units', 0)
                r += f'<td>{_fmt(u) if u else ""}</td>'
            for p in ice_pl:
                v = pdata.get(p, {}).get('value', 0)
                r += f'<td>{_fc(v) if v else ""}</td>'
            r += f'<td class="tot">{_fmt(ctu)}</td><td class="tot">{_fc(ctv)}</td>'
            ice_rows_data.append((ctv, f'<tr>{r}</tr>'))
    ice_rows_data.sort(key=lambda x: x[0], reverse=True)
    ice_rows = '\n'.join(r for _, r in ice_rows_data)

    ice_tbl = (f'<div class="card full" style="margin-bottom:14px"><h3>Icedream Customers - By Product</h3>'
               f'<table class="tbl"><thead><tr><th>Month</th><th>Customer</th>{ice_h}'
               f'<th>Total Units</th><th>Total ₪</th></tr></thead>'
               f'<tbody>{ice_rows}</tbody></table></div>') if ice_rows_data else ''

    # ── Ma'ayan Chains (aggregated by normalized chain name, sorted by revenue desc) ──
    may_pl = [p for p in ['chocolate', 'vanilla', 'mango', 'pistachio'] if p in active_products]
    may_h = ''.join(f'<th>{PRODUCT_SHORT[p]} (units)</th>' for p in may_pl)
    may_h += ''.join(f'<th>{PRODUCT_SHORT[p]} (₪)</th>' for p in may_pl)
    may_rows_data = []
    for month in month_list:
        md = data['monthly_data'][month]
        mh = MONTH_NAMES_HEB.get(month, month)
        cr = md.get('mayyan_accounts_revenue', {})
        # Aggregate accounts by normalized chain name (splits טיב טעם from שוק פרטי, דור אלון into AMPM/אלונית)
        norm_chains = {}
        for key, pdata in cr.items():
            # key is (chain_name, account_name) tuple
            source_chain, acct = key if isinstance(key, tuple) else ('', key)
            norm = extract_chain_name(acct, source_chain=source_chain)
            if norm not in norm_chains:
                norm_chains[norm] = {}
            for p in may_pl:
                if p not in norm_chains[norm]:
                    norm_chains[norm][p] = {'units': 0, 'value': 0}
                pd_ = pdata.get(p, {})
                if isinstance(pd_, dict):
                    norm_chains[norm][p]['units'] += pd_.get('units', 0)
                    norm_chains[norm][p]['value'] += pd_.get('value', 0)
        for chain, pdata in norm_chains.items():
            ctu = sum(pdata.get(p, {}).get('units', 0) for p in may_pl)
            ctv = sum(pdata.get(p, {}).get('value', 0) for p in may_pl)
            if ctu == 0:
                continue
            r = f'<td>{mh}</td><td><b>{chain}</b></td>'
            for p in may_pl:
                u = pdata.get(p, {}).get('units', 0)
                r += f'<td>{_fmt(u) if u else ""}</td>'
            for p in may_pl:
                v = pdata.get(p, {}).get('value', 0)
                r += f'<td>{_fc(v) if v else ""}</td>'
            r += f'<td class="tot">{_fmt(ctu)}</td><td class="tot">{_fc(ctv)}</td>'
            may_rows_data.append((ctv, f'<tr>{r}</tr>'))
    may_rows_data.sort(key=lambda x: x[0], reverse=True)
    may_rows = '\n'.join(r for _, r in may_rows_data)

    may_tbl = (f'<div class="card full" style="margin-bottom:14px"><h3>Ma\'ayan Chains - By Product</h3>'
               f'<table class="tbl"><thead><tr><th>Month</th><th>Chain</th>{may_h}'
               f'<th>Total Units</th><th>Total ₪</th></tr></thead>'
               f'<tbody>{may_rows}</tbody></table></div>') if may_rows_data else ''

    # ── Top Customers (aggregated by chain) ──
    all_c = {}
    for month in month_list:
        md = data['monthly_data'][month]
        for c, pd in md.get('icedreams_customers', {}).items():
            chain = extract_chain_name(c)
            all_c[chain] = all_c.get(chain, 0) + sum(pd.get(p, {}).get('units', 0) for p in active_products)
        for key, pd in md.get('mayyan_accounts_revenue', {}).items():
            source_chain, acct = key if isinstance(key, tuple) else ('', key)
            norm = extract_chain_name(acct, source_chain=source_chain)
            k = f"Ma'ayan: {norm}"
            all_c[k] = all_c.get(k, 0) + sum(pd.get(p, {}).get('units', 0) for p in active_products if isinstance(pd.get(p), dict))
    all_c = {k: v for k, v in all_c.items() if v > 0}
    tc_list = sorted(all_c.items(), key=lambda x: x[1], reverse=True)[:10]
    mc = tc_list[0][1] if tc_list else 1
    top_bars = _bar_html(tc_list, mc, '#6366f1')
    top_tbl = f'<div class="card full" style="margin-bottom:14px"><h3>Top Customers (units)</h3>{top_bars}</div>' if tc_list else ''

    # Flavor analysis - for all views
    flavor_section = _build_flavor_analysis(data, month_list, is_all)

    # Inventory section - only in overview
    inv_section = _build_inventory_section(data) if is_all else ''

    display = 'block' if section_id == 'all-ab' else 'none'
    return (f'<div class="month-section" id="sec-{section_id}" style="display:{display}">\n'
            f'{kpis}\n{rev_card}\n{units_card}\n{flavor_section}\n{inv_section}\n{summary_tbl}\n{ice_tbl}\n{may_tbl}\n{top_tbl}\n</div>')


BRAND_FILTERS = {
    'ab': {'label': 'All Brands', 'products': ['chocolate', 'vanilla', 'mango', 'dream_cake', 'magadat', 'pistachio']},
    'turbo': {'label': 'Turbo', 'products': ['chocolate', 'vanilla', 'mango', 'pistachio', 'magadat']},
    'danis': {'label': "Dani's", 'products': ['dream_cake']},
}

def generate_dashboard(data):
    """Generate static HTML dashboard with month + brand filters."""
    months = data['months']
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    # Build month filter buttons
    filter_ids = ['all'] + [f'm{i}' for i in range(len(months))]
    filter_labels = ['Overview'] + [MONTH_NAMES_HEB.get(m, m) for m in months]
    month_btn_html = ''
    for fid, flabel in zip(filter_ids, filter_labels):
        active = ' fbtn-active' if fid == 'all' else ''
        month_btn_html += f'<button class="fbtn month-btn{active}" onclick="setMonth(\'{fid}\')">{flabel}</button>\n'

    # Build brand filter buttons
    brand_btn_html = ''
    for bid, binfo in BRAND_FILTERS.items():
        active = ' fbtn-active' if bid == 'ab' else ''
        brand_btn_html += f'<button class="fbtn brand-btn{active}" onclick="setBrand(\'{bid}\')">{binfo["label"]}</button>\n'

    btn_html = (f'<span>Period:</span> {month_btn_html}'
                f'<span style="margin-left:16px">Brand:</span> {brand_btn_html}')

    # Build sections: one per (month × brand) combination
    sections = ''
    for fid, _ in zip(filter_ids, filter_labels):
        if fid == 'all':
            month_list = months
        else:
            idx = int(fid[1:])
            month_list = [months[idx]]
        for bid, binfo in BRAND_FILTERS.items():
            sec_id = f'{fid}-{bid}'
            active_products = binfo['products']
            sections += _build_month_section(data, month_list, sec_id, active_products)

    html = f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Raito Business Overview</title>
<style>
:root {{ --bg:#f0f2f5; --card:#fff; --text:#1a1a2e; --text2:#555; --border:#e0e0e0; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Tahoma,sans-serif; background:var(--bg); color:var(--text); direction:ltr; }}
.hdr {{ background:linear-gradient(135deg,#1e3a5f,#2563eb); color:#fff; padding:20px 32px; }}
.hdr h1 {{ font-size:22px; }} .hdr .sub {{ opacity:.8; font-size:13px; margin-top:4px; }}
.hdr .brands {{ display:flex; gap:24px; margin-top:8px; font-size:12px; opacity:.7; }}
.fbar {{ background:var(--card); padding:12px 32px; border-bottom:1px solid var(--border); display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
.fbar span {{ font-weight:600; font-size:13px; margin-left:8px; }}
.fbtn {{ padding:7px 16px; border:1px solid var(--border); border-radius:8px; background:#fff; font-size:13px; cursor:pointer; font-family:inherit; }}
.fbtn:hover {{ background:#e8f0fe; }}
.fbtn-active {{ background:#2563eb; color:#fff; border-color:#2563eb; }}
.ctr {{ max-width:1440px; margin:0 auto; padding:20px; }}
.kpis {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:20px; }}
.kpi {{ background:var(--card); border-radius:10px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
.kpi .l {{ font-size:12px; color:var(--text2); margin-bottom:6px; }}
.kpi .v {{ font-size:24px; font-weight:700; }}
.kpi-title {{ font-size:16px; font-weight:700; color:#1e3a5f; margin-bottom:10px; border-bottom:2px solid #2563eb; padding-bottom:5px; text-align:center; }}
.kpi .v.green {{ color:#10b981; }} .kpi .v.blue {{ color:#2563eb; }}
.card {{ background:var(--card); border-radius:10px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
.card.full {{ width:100%; }}
.card h3 {{ font-size:14px; margin-bottom:10px; color:#1e3a5f; }}
.tbl {{ width:100%; border-collapse:collapse; font-size:12px; margin-top:8px; }}
.tbl th {{ background:#2C3E50; color:#fff; padding:8px 6px; text-align:center; font-weight:600; }}
.tbl td {{ padding:6px; text-align:center; border-bottom:1px solid var(--border); }}
.tbl tr:hover {{ background:#f8f9fa; }}
.tbl .tot {{ font-weight:700; background:#f0f0f0; }}
.badge {{ display:inline-block; padding:1px 6px; border-radius:8px; font-size:10px; font-weight:600; }}
.badge.disc {{ background:#fee2e2; color:#dc2626; }}
.badge.new {{ background:#d1fae5; color:#059669; }}
.notes {{ background:var(--card); border-radius:10px; padding:16px; margin-top:12px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
.notes h3 {{ margin-bottom:6px; font-size:14px; }} .notes ul {{ padding-left:18px; font-size:13px; color:var(--text2); }} .notes li {{ margin-bottom:3px; }}
.ts {{ text-align:center; padding:12px; color:var(--text2); font-size:11px; }}
@media (max-width:900px) {{ .kpis {{ grid-template-columns:repeat(2,1fr); }} }}
</style>
</head>
<body>
<div class="hdr">
  <h1>Raito Business Overview</h1>
  <div class="sub">Inventory, Sales &amp; Distribution</div>
  <div class="brands">
    <span>Turbo Ice Cream | Danny Avdia</span>
    <span>Dani's Dream Cake | Daniel Amit</span>
    <span>Distributors: Icedream | Ma'ayan</span>
  </div>
</div>
<div class="fbar">
  <span>View:</span>
  {btn_html}
</div>
<div class="ctr">
  {sections}
  <div class="notes"><h3>Notes</h3><ul>
    <li><span class="badge disc">Disc.</span> Turbo Magadat - sold until stock runs out</li>
    <li><span class="badge new">New</span> Turbo Pistachio - launching Feb 2026</li>
    <li>Dani's Dream Cake - switching to Biscotti distribution from 1.3.2026</li>
  </ul></div>
  <div class="ts">Auto-generated | {now_str}</div>
</div>
<script>
var curMonth='all', curBrand='ab';
function updateView(){{
  document.querySelectorAll('.month-section').forEach(function(s){{s.style.display='none';}});
  var el=document.getElementById('sec-'+curMonth+'-'+curBrand);
  if(el) el.style.display='block';
}}
function setMonth(id){{
  curMonth=id;
  document.querySelectorAll('.month-btn').forEach(function(b){{b.classList.remove('fbtn-active');}});
  event.target.classList.add('fbtn-active');
  updateView();
}}
function setBrand(id){{
  curBrand=id;
  document.querySelectorAll('.brand-btn').forEach(function(b){{b.classList.remove('fbtn-active');}});
  event.target.classList.add('fbtn-active');
  updateView();
}}
</script>
</body></html>"""

    out = OUTPUT_DIR / 'dashboard.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Dashboard saved: {out}")
    return out
