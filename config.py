#!/usr/bin/env python3
"""
Raito Dashboard — Shared Configuration
Product definitions, pricing, colors, month mappings, and brand filters.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR.parent / 'data'
OUTPUT_DIR = BASE_DIR.parent / 'docs'

# ── Product Classification ──────────────────────────────────────────────

PRODUCT_NAMES = {
    'chocolate': 'Turbo Chocolate',
    'vanilla': 'Turbo Vanilla',
    'mango': 'Turbo Mango',
    'magadat': 'Turbo Magadat',
    'dream_cake': "Dani's Dream Cake",
    'pistachio': 'Turbo Pistachio',
}

PRODUCT_SHORT = {
    'chocolate': 'Chocolate',
    'vanilla': 'Vanilla',
    'mango': 'Mango',
    'magadat': 'Magadat',
    'dream_cake': 'Dream Cake',
    'pistachio': 'Pistachio',
}

PRODUCT_STATUS = {
    'chocolate': 'active',
    'vanilla': 'active',
    'mango': 'active',
    'magadat': 'discontinued',
    'dream_cake': 'active',
    'pistachio': 'new',
}

PRODUCT_COLORS = {
    'chocolate': '#8B4513',
    'vanilla': '#F5DEB3',
    'mango': '#FF8C00',
    'magadat': '#999999',
    'dream_cake': '#4A0E0E',
    'pistachio': '#93C572',
}

FLAVOR_COLORS = {
    'chocolate': '#8B4513', 'vanilla': '#DAA520', 'mango': '#FF8C00',
    'pistachio': '#93C572', 'dream_cake': '#DB7093', 'magadat': '#9CA3AF',
}

# Standard product order for tables and charts
PRODUCTS_ORDER = ['chocolate', 'vanilla', 'mango', 'pistachio', 'dream_cake', 'magadat']

# ── Pricing & Costs ─────────────────────────────────────────────────────

PRODUCTION_COST = {
    'chocolate': 6.5, 'vanilla': 6.5, 'mango': 6.5, 'pistachio': 7.1,
    'dream_cake': 53.5,
}

SELLING_PRICE_B2B = {
    'chocolate': 13.8, 'vanilla': 13.8, 'mango': 13.8, 'pistachio': 13.8,
    'dream_cake': 81.1,
}

SELLING_PRICE_B2C = {
    'dream_cake': 81.1,
}

# ── Inventory & Planning ────────────────────────────────────────────────

TARGET_MONTHS_STOCK = 1  # Target months of inventory to maintain
PALLET_DIVISOR = 2400    # Units per pallet

# ── Brand & Creator Info ────────────────────────────────────────────────

DISTRIBUTOR_NAMES = {
    'icedreams': 'Icedream',
    'mayyan': 'מעיין נציגויות',
}

CREATORS = [
    {'name': 'דני אבדיה', 'brand': 'Turbo',
     'products': ['chocolate', 'vanilla', 'mango', 'pistachio']},
    {'name': 'דניאל עמית', 'brand': "Dani's",
     'products': ['dream_cake']},
]

BRAND_FILTERS = {
    'ab': {'label': 'All Brands',
            'products': ['chocolate', 'vanilla', 'mango', 'dream_cake', 'magadat', 'pistachio']},
    'turbo': {'label': 'Turbo',
              'products': ['chocolate', 'vanilla', 'mango', 'pistachio', 'magadat']},
    'danis': {'label': "Dani's",
              'products': ['dream_cake']},
}

# ── Month Mappings ──────────────────────────────────────────────────────

MONTH_ORDER = {
    'October 2025': 0, 'December 2025': 1, 'January 2026': 2,
    'February 2026': 3, 'March 2026': 4, 'April 2026': 5, 'May 2026': 6,
    'June 2026': 8, 'July 2026': 9, 'August 2026': 10, 'September 2026': 11,
}

MONTH_NAMES_HEB = {
    'October 2025': "Oct '25", 'December 2025': "Dec '25",
    'January 2026': "Jan '26", 'February 2026': "Feb '26", 'March 2026': "Mar '26",
    'April 2026': "Apr '26", 'May 2026': "May '26", 'June 2026': "Jun '26",
    'July 2026': "Jul '26", 'August 2026': "Aug '26", 'September 2026': "Sep '26",
}

CHART_MONTHS = list(MONTH_ORDER.keys())

# ── Shared Helpers ──────────────────────────────────────────────────────

import re

def classify_product(name):
    if name is None:
        return None
    name = str(name)
    # Exclude non-Raito products
    if 'באגסו' in name or 'דובאי' in name:
        return None
    if 'וניל' in name:
        return 'vanilla'
    elif 'מנגו' in name:
        return 'mango'
    elif 'שוקולד' in name:
        return 'chocolate'
    elif 'מארז' in name:
        return 'magadat'
    elif 'דרים' in name:
        return 'dream_cake'
    elif 'פיסטוק' in name:
        return 'pistachio'
    return None

# Known chain prefixes for Icedream customer aggregation
_CHAIN_PREFIXES = [
    'דומינוס פיצה', 'דומינוס', 'גוד פארם', 'חוות נעמי', 'נוי השדה',
    'וואלט', 'וולט', 'ינגו', 'כרמלה', 'עוגיפלצת',
]

def extract_chain_name(customer_name, source_chain=None):
    """Extract chain/brand name from a branch-level customer name.

    Args:
        customer_name: The account/branch name to classify.
        source_chain: Optional original chain name from Ma'ayan data.
            When provided and the account name doesn't match any known
            pattern, returns the source chain instead of the raw name.
    """
    if not customer_name:
        return customer_name
    s = str(customer_name).strip()
    # Normalize all Wolt variants to "וולט מרקט"
    if 'וולט' in s or 'וואלט' in s:
        return 'וולט מרקט'
    # Normalize Paz Yellow variants to "פז ילו"
    if 'פז יילו' in s or 'פז ילו' in s:
        return 'פז ילו'
    # Split טיב טעם out of שוק פרטי
    if 'טיב טעם' in s:
        return 'טיב טעם'
    # Split דור אלון into אלונית and AMPM
    if s.startswith('דור אלון'):
        if 'AM:PM' in s or 'AMPM' in s or 'am:pm' in s.lower():
            return 'AMPM'
        if 'אלונית' in s:
            return 'אלונית'
        return 'דור אלון'
    for prefix in _CHAIN_PREFIXES:
        if s.startswith(prefix):
            if prefix == 'דומינוס פיצה':
                return 'דומינוס'
            return prefix
    # For Ma'ayan accounts: fall back to the source chain name if provided
    if source_chain:
        sc = str(source_chain).strip()
        # Normalize the source chain name too
        if 'פז יילו' in sc or 'פז ילו' in sc:
            return 'פז ילו'
        return sc
    return s

def extract_units_per_carton(name):
    if name is None:
        return 1
    match = re.search(r'[\*\-]\s*(\d+)\s*יח', str(name))
    return int(match.group(1)) if match else 1

def pallets(units, product=None):
    """Convert units to pallets (1 decimal). Dream cake returns '-'."""
    if product == 'dream_cake':
        return '-'
    return round(units / PALLET_DIVISOR, 1) if units > 0 else 0

def fmt(n):
    """Format number with commas."""
    return f'{int(n):,}'

def fc(n):
    """Format currency."""
    return f'₪{int(round(n)):,}'

def compute_kpis(data, month_list, filter_products=None):
    """Compute KPIs for given months, optionally filtered by products."""
    products = filter_products if filter_products else data['products']
    tu = tr = tc = tgm = tmy = tic = 0
    for month in month_list:
        md = data['monthly_data'].get(month, {})
        for p in products:
            c = md.get('combined', {}).get(p, {})
            u = c.get('units', 0)
            if u > 0:
                tu += u
                tr += c.get('total_value', 0)
                tc += c.get('production_cost', 0)
                tgm += c.get('gross_margin', 0)
                tmy += c.get('mayyan_units', 0)
                tic += c.get('icedreams_units', 0)
    td = tmy + tic
    mp = round(tmy / td * 100) if td > 0 else 0
    return tu, tr, tc, tgm, tmy, tic, mp, 100 - mp

def count_pos(data, month_list):
    """Count unique points of sale across months."""
    ice_custs = set()
    may_branches = set()
    for month in month_list:
        md = data['monthly_data'].get(month, {})
        for c in md.get('icedreams_customers', {}):
            ice_custs.add(c)
        for b in md.get('mayyan_branches', set()):
            may_branches.add(b)
    return len(ice_custs) + len(may_branches)
