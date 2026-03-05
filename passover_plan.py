#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
תוכנית ייצור לפסח — גלידת חלבון (מותג דני אבדיה / Turbo)
Passover Production Plan — Protein Ice Cream (Dani Avdiya / Turbo Brand)
=============================================================================

הנחות עבודה מרכזיות:
  1. החל מתוכנית פסח, מעיין נציגויות ואייסדרים רוכשים ישירות מהיצרן.
  2. המלאי הקיים (מחסן + מפיצים) אינו כשר לפסח — אין תווית כשל"פ.
     לכן אין קיזוז מלאי קיים מהביקוש לפסח; כל הביקוש מכוסה בייצור חדש.
  3. חלון מכירות כשל"פ: 09/03/2026 – 26/03/2026 (18 ימים).
     לאחר 26/03 המפיצים חוזרים לגרסה הרגילה — לא רצוי יתרות מלאי גבוהות.
  4. הביקוש מחושב כ: קצב יומי פברואר × 18 ימי מכירות × גורם עונתיות פסח.
  5. Dream Cake לא רלוונטי לתוכנית פסח — הוסר לחלוטין.

=============================================================================
"""

import sys
import math
import warnings
from datetime import date, timedelta

import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 160)
pd.set_option('display.float_format', lambda x: f'{x:,.1f}')

# ─────────────────────────────────────────────────────────────────────────────
# 0. CONSTANTS & PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

PALLET_SIZE = 2_400                            # יחידות למשטח

# ── תאריכים ──
PRODUCTION_START_DATE  = date(2026, 3, 8)     # תחילת ייצור כשל"פ (ראשון יום לפני המכירות)
PASSOVER_SALES_START   = date(2026, 3, 9)     # פתיחת חלון מכירות מפיצים → לקוחות
PASSOVER_SALES_END     = date(2026, 3, 26)    # סגירת חלון מכירות כשל"פ
PASSOVER_SALES_DAYS    = (PASSOVER_SALES_END - PASSOVER_SALES_START).days + 1   # = 18
PRODUCTION_DEADLINE    = PASSOVER_SALES_END   # ייצור חייב להסתיים לכל המאוחר ביום האחרון למכירות

FEB_MTD_DAYS           = 26                   # ימים שנקלטו בנתוני פברואר (MTD עד 26.2)

# ── קיבולת ──
PRODUCTION_DAYS_PER_WEEK  = 6                 # ראשון–שישי (ללא שבת)
DAILY_CAPACITY_PALLETS    = 4                 # 4 משטחים/יום = 9,600 יח׳
                                               # None = ללא אילוץ קיבולת

# ── מלאי קיים ──
# המלאי הקיים אינו כשל"פ (אין תווית) — לא מקוזז מהביקוש לפסח
EXISTING_STOCK_KOSHER_FOR_PASSOVER = False    # ← False = לא מקוזז

# ── גורם עונתיות ברירת מחדל ──
DEFAULT_PASSOVER_GROWTH = 1.5

# ── גודל מינימלי להזמנה ──
DEFAULT_MIN_ORDER_BATCH = PALLET_SIZE          # עיגול למשטח שלם

# מוצרים רלוונטיים לפסח (dream_cake הוסר)
PRODUCTS = ['chocolate', 'vanilla', 'mango', 'pistachio', 'magadat']

# ─────────────────────────────────────────────────────────────────────────────
# 1. FEBRUARY WAREHOUSE WITHDRAWALS
#    משיכות ממחסן קרפרי בפברואר 2026 — מוצג לשקיפות, לא מקוזז מביקוש הפסח
#    (המלאי שנמשך הופץ ונמכר ואינו כשל"פ)
# ─────────────────────────────────────────────────────────────────────────────

FEB_WITHDRAWALS_PALLETS: dict[str, dict[str, int]] = {
    'mayyan': {
        'chocolate': 6,   # 14,400 יח׳
        'vanilla':   6,   # 14,400 יח׳
        'mango':     1,   #  2,400 יח׳
    },
    'icedream': {
        'vanilla':   1,   #  2,400 יח׳
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def u2p(units: float) -> float:
    """יחידות → משטחים (עיגול לספרה אחת)."""
    return round(units / PALLET_SIZE, 1)


def p2u(pallets: float) -> int:
    """משטחים → יחידות (שלם)."""
    return int(round(pallets * PALLET_SIZE))


# ─────────────────────────────────────────────────────────────────────────────
# 3. DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_live_data():
    """Load Feb 2026 sales + inventory from existing parsers."""
    sys.path.insert(0, '/sessions/vibrant-fervent-gauss/mnt/dataset')
    from parsers import consolidate_data   # type: ignore

    data    = consolidate_data()
    feb     = data['monthly_data'].get('February 2026', {})
    combined = feb.get('combined', {})

    feb_sales = {
        'mayyan':   {p: combined[p]['mayyan_units']    for p in combined},
        'icedream': {p: combined[p]['icedreams_units'] for p in combined},
    }
    return feb_sales, data.get('warehouse', {}), data.get('dist_inv', {})


def get_sample_data():
    """Fallback hardcoded sample data."""
    feb_sales = {
        'mayyan':   {'chocolate': 9707, 'vanilla': 10020, 'mango': 6085,
                     'pistachio': 7650, 'magadat': 0},
        'icedream': {'chocolate': 1516, 'vanilla': 1272,  'mango': 686,
                     'pistachio': 2600, 'magadat': 1374},
    }
    warehouse_inv = {
        'total_units': 71_430,
        'products': {
            'chocolate': {'units': 16_800},
            'vanilla':   {'units': 25_830},
            'mango':     {'units': 28_800},
            'pistachio': {'units': 0},
            'magadat':   {'units': 0},
        },
    }
    dist_inv = {
        'icedream': {
            'total_units': 9_502,
            'products': {
                'chocolate': {'units': 886},
                'vanilla':   {'units': 2_415},
                'mango':     {'units': 1_895},
                'pistachio': {'units': 3_227},
                'magadat':   {'units': 204},
            },
        },
        'mayyan': {
            'total_units': 12_404,
            'products': {
                'chocolate': {'units': 4_454},
                'vanilla':   {'units': 4_209},
                'mango':     {'units': 3_741},
            },
        },
    }
    return feb_sales, warehouse_inv, dist_inv


def load_data():
    """Try live parsers; fall back to sample data."""
    try:
        result = load_live_data()
        print("✓ נתונים נטענו בהצלחה מהקבצים האמיתיים (live parsers).\n")
        return *result, True
    except Exception as exc:
        warnings.warn(f"⚠️  לא ניתן לטעון parsers ({exc}). משתמש בנתוני דוגמה.", RuntimeWarning)
        print("⚠️  משתמש בנתוני דוגמה (sample data).\n")
        return *get_sample_data(), False


# ─────────────────────────────────────────────────────────────────────────────
# 4. DISTRIBUTOR PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

DISTRIBUTOR_PARAMS: dict = {
    'mayyan': {
        'display_name': 'מעיין נציגויות',
        'growth_factor_passover': {
            'chocolate': 1.5,
            'vanilla':   1.5,
            'mango':     0.0,    # ← אין ייצור כשל"פ — פיסטוק לוקח את הנתח
            'pistachio': 1.6,
            'magadat':   0.0,    # לא רלוונטי
        },
        # מלאי ביטחון = 0 — לא רוצים יתרות אחרי 26/3
        'safety_stock_pallets': {
            'chocolate': 0,
            'vanilla':   0,
            'mango':     0,
            'pistachio': 0,
            'magadat':   0,
        },
        'min_order_batch': DEFAULT_MIN_ORDER_BATCH,
    },
    'icedream': {
        'display_name': 'אייסדרים',
        'growth_factor_passover': {
            'chocolate': 1.5,
            'vanilla':   1.5,
            'mango':     0.0,    # ← אין ייצור כשל"פ — פיסטוק לוקח את הנתח
            'pistachio': 1.6,
            'magadat':   0.0,
        },
        'safety_stock_pallets': {
            'chocolate': 0,
            'vanilla':   0,
            'mango':     0,
            'pistachio': 0,
            'magadat':   0,
        },
        'min_order_batch': DEFAULT_MIN_ORDER_BATCH,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 5. VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_non_negative(value: float, label: str) -> None:
    if value < 0:
        raise ValueError(f"ערך שלילי לא חוקי: {label} = {value:.1f}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. FORECAST — based on Passover sales window (not full-month projection)
# ─────────────────────────────────────────────────────────────────────────────

def build_forecast(feb_sales: dict, dist_params: dict) -> pd.DataFrame:
    """
    Passover demand forecast per distributor × product.

    Formula:
        daily_rate      = feb_mtd_sales / FEB_MTD_DAYS        (יחידות ביום)
        passover_demand = daily_rate × PASSOVER_SALES_DAYS × growth_factor

    משמעות: כמה יחידות ימכרו בחלון המכירות הפסחי (18 ימים), בהנחת גורם עונתיות.

    הערה: מלאי ביטחון = 0 — לא רוצים יתרות כשל"פ אחרי 26/03/2026.
    """
    rows = []
    for dist_key, params in dist_params.items():
        dist_name = params['display_name']
        for product in PRODUCTS:
            feb_mtd  = feb_sales.get(dist_key, {}).get(product, 0)
            growth   = params['growth_factor_passover'].get(product, DEFAULT_PASSOVER_GROWTH)
            safety_p = params['safety_stock_pallets'].get(product, 0)
            safety_u = safety_p * PALLET_SIZE

            validate_non_negative(feb_mtd, f"{dist_name}/{product}/feb_mtd")
            validate_non_negative(growth,  f"{dist_name}/{product}/growth_factor")

            if growth == 0:
                # מוצר לא רלוונטי לפסח עבור מפיץ זה
                continue

            daily_rate        = feb_mtd / FEB_MTD_DAYS
            passover_demand_u = daily_rate * PASSOVER_SALES_DAYS * growth + safety_u

            rows.append({
                'distributor_key':           dist_key,
                'distributor':               dist_name,
                'product':                   product,
                'feb_sales_mtd_units':       round(feb_mtd),
                'feb_sales_mtd_pallets':     u2p(feb_mtd),
                'feb_daily_rate_units':      round(daily_rate, 1),
                'growth_factor_passover':    growth,
                'passover_sales_days':       PASSOVER_SALES_DAYS,
                'forecast_passover_units':   round(passover_demand_u),
                'forecast_passover_pallets': u2p(passover_demand_u),
                'kosher_for_passover':       True,
            })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 7. NET PRODUCTION REQUIREMENTS
#    אין קיזוז מלאי (מלאי קיים אינו כשל"פ) — כל הביקוש = ייצור חדש
# ─────────────────────────────────────────────────────────────────────────────

def compute_net_requirements(df: pd.DataFrame, dist_params: dict) -> pd.DataFrame:
    """
    Net production = ceil(passover_demand / pallet_size) × pallet_size
    (עיגול למשטח שלם)
    No stock offset — existing inventory has no KFP label.
    """
    df = df.copy()
    net_units_list   = []
    net_pallets_list = []

    for _, row in df.iterrows():
        dist_key  = row['distributor_key']
        min_batch = dist_params[dist_key]['min_order_batch']
        demand    = row['forecast_passover_units']

        validate_non_negative(demand, f"{row['distributor']}/{row['product']}/demand")

        net = math.ceil(demand / min_batch) * min_batch if min_batch > 1 and demand > 0 \
              else math.ceil(demand)

        net_units_list.append(net)
        net_pallets_list.append(u2p(net))

    df['net_production_units']   = net_units_list
    df['net_production_pallets'] = net_pallets_list
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 8. PRODUCTION SCHEDULE
# ─────────────────────────────────────────────────────────────────────────────

def get_working_days(start: date, end: date, days_per_week: int = 6) -> list[date]:
    """Return working days [start..end]. days_per_week=6 skips Saturday only."""
    working, current = [], start
    while current <= end:
        wd = current.weekday()   # Mon=0, Sun=6
        if days_per_week == 6 and wd != 5:
            working.append(current)
        elif days_per_week == 5 and wd < 5:
            working.append(current)
        current += timedelta(days=1)
    return working


def build_production_schedule(
    net_req_df: pd.DataFrame,
    production_start: date         = PRODUCTION_START_DATE,
    deadline: date                 = PRODUCTION_DEADLINE,
    daily_capacity_pallets: int | None = DAILY_CAPACITY_PALLETS,
    days_per_week: int             = PRODUCTION_DAYS_PER_WEEK,
) -> tuple[pd.DataFrame | None, pd.DataFrame]:
    """
    Schedule Passover production (pallets/day, heavy products first).
    Returns (schedule_df, capacity_summary_df).
    """
    prod_df = net_req_df[net_req_df['net_production_pallets'] > 0].copy()

    product_totals = (
        prod_df.groupby('product')['net_production_pallets']
        .sum()
        .reset_index()
        .rename(columns={'net_production_pallets': 'total_pallets'})
    )
    product_totals['total_units'] = (product_totals['total_pallets'] * PALLET_SIZE).astype(int)
    total_pallets = product_totals['total_pallets'].sum()

    working_days   = get_working_days(production_start, deadline, days_per_week)
    n_working_days = len(working_days)
    total_cap_p    = n_working_days * daily_capacity_pallets if daily_capacity_pallets else None

    # ─── היתכנות ───
    feasibility_rows = []
    for _, row in product_totals.iterrows():
        pallets = row['total_pallets']
        if total_cap_p is not None:
            pct         = pallets / total_pallets if total_pallets > 0 else 0
            cap_p       = round(total_cap_p * pct, 1)
            feasible    = cap_p >= pallets
            surplus_def = round(cap_p - pallets, 1)
        else:
            cap_p = surplus_def = None
            feasible = True

        feasibility_rows.append({
            'product':                row['product'],
            'משטחים לייצור':          pallets,
            'יחידות לייצור':          row['total_units'],
            'ימי ייצור זמינים':       n_working_days,
            'קיבולת/יום (מש׳)':      daily_capacity_pallets or 'N/A',
            'קיבולת כוללת (מש׳)':    total_cap_p or 'N/A',
            'אפשרי?':                 feasible,
            'עודף/גרעון (מש׳)':      surplus_def,
            'כשל"פ':                  True,
        })

    capacity_summary = pd.DataFrame(feasibility_rows)

    # ─── בדיקה כוללת ───
    if total_cap_p is not None:
        if total_pallets > total_cap_p:
            gap = total_pallets - total_cap_p
            min_cap = math.ceil(total_pallets / n_working_days)
            warnings.warn(
                f"\n{'='*70}\n"
                f"⚠️  אזהרת קיבולת!\n"
                f"   נדרש:   {total_pallets:.0f} משטחים\n"
                f"   זמין:   {total_cap_p:.0f} משטחים\n"
                f"   גרעון:  {gap:.0f} משטחים\n"
                f"   פתרון: הגדל קיבולת ל-{min_cap} מש׳/יום "
                f"או התחל לפני {production_start.strftime('%d/%m/%Y')}\n"
                f"{'='*70}",
                UserWarning, stacklevel=2,
            )
        else:
            days_needed = math.ceil(total_pallets / daily_capacity_pallets) if daily_capacity_pallets else '?'
            print(
                f"✓ קיבולת מספיקה: {total_pallets:.0f} משטחים נדרשים.\n"
                f"  בקיבולת {daily_capacity_pallets} מש׳/יום: יסתיים תוך {days_needed} ימי עבודה "
                f"(עד {working_days[days_needed - 1].strftime('%d/%m/%Y') if isinstance(days_needed, int) and days_needed <= len(working_days) else '?'}).\n"
            )

    if daily_capacity_pallets is None or not working_days:
        return None, capacity_summary

    # ─── שיבוץ יומי ───
    remaining = (
        product_totals
        .sort_values('total_pallets', ascending=False)
        .set_index('product')['total_pallets']
        .to_dict()
    )

    schedule_rows = []
    for day in working_days:
        cap_today = daily_capacity_pallets
        for product, need in list(remaining.items()):
            if cap_today <= 0 or need <= 0:
                continue
            produce  = min(need, cap_today)
            schedule_rows.append({
                'תאריך':    day.strftime('%d/%m/%Y'),
                'יום':      _heb_weekday(day),
                'מוצר':     product,
                'משטחים':   round(produce, 1),
                'יחידות':   p2u(produce),
                'כשל"פ':    True,
            })
            remaining[product] = round(need - produce, 1)
            cap_today = round(cap_today - produce, 1)
        if all(v <= 0 for v in remaining.values()):
            break   # ייצור הסתיים

    return pd.DataFrame(schedule_rows), capacity_summary


def _heb_weekday(d: date) -> str:
    return {0: 'שני', 1: 'שלישי', 2: 'רביעי', 3: 'חמישי', 4: 'שישי', 5: 'שבת', 6: 'ראשון'}.get(
        d.weekday(), ''
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. REPORTING
# ─────────────────────────────────────────────────────────────────────────────

W = 130
SEP  = '─' * W
SEP2 = '═' * W


def section(title: str) -> None:
    print(f"\n{SEP2}\n  {title}\n{SEP2}")


def print_inventory_context(warehouse_inv: dict, dist_inv: dict) -> None:
    """Print current inventory for context (not offset from demand)."""
    print("  הערה: מלאי זה אינו כשל\"פ — לא מקוזז מביקוש הפסח.\n")

    rows = []
    for p in PRODUCTS:
        wh_u  = warehouse_inv.get('products', {}).get(p, {}).get('units', 0)
        ice_u = dist_inv.get('icedream', {}).get('products', {}).get(p, {}).get('units', 0)
        may_u = dist_inv.get('mayyan',   {}).get('products', {}).get(p, {}).get('units', 0)
        total = wh_u + ice_u + may_u
        if total == 0:
            continue
        rows.append({
            'מוצר':                     p,
            'מחסן Karfree (מש׳)':       u2p(wh_u),
            'אייסדרים (מש׳)':           u2p(ice_u),
            'מעיין (מש׳)':              u2p(may_u),
            'סה"כ קיים (מש׳)':          u2p(total),
            'סה"כ קיים (יח׳)':          total,
        })
    if rows:
        print(pd.DataFrame(rows).to_string(index=False))

    print()
    print("  משיכות מחסן בפברואר 2026 (לידיעה):")
    for dist_key, withdrawals in FEB_WITHDRAWALS_PALLETS.items():
        dname = DISTRIBUTOR_PARAMS.get(dist_key, {}).get('display_name', dist_key)
        parts = [f"{p} {n} מש׳" for p, n in withdrawals.items()]
        print(f"    {dname}: {', '.join(parts)}")


def print_forecast_table(df: pd.DataFrame) -> None:
    """Forecast per distributor × product in pallets."""
    cols = [
        'distributor', 'product',
        'feb_sales_mtd_pallets', 'feb_daily_rate_units',
        'growth_factor_passover', 'passover_sales_days',
        'forecast_passover_pallets', 'net_production_pallets',
        'kosher_for_passover',
    ]
    display = df[cols].copy()
    display.columns = [
        'מפיץ', 'מוצר',
        'מכירות פבר׳ (מש׳)', 'קצב יומי פבר׳ (יח׳)',
        'גורם עונתי', 'ימי מכירה',
        'ביקוש פסח (מש׳)', 'ייצור נדרש (מש׳)',
        'כשל"פ',
    ]
    print(display.to_string(index=False))


def print_totals(df: pd.DataFrame) -> None:
    print()
    print(SEP)
    total_lbl = 'סה"כ כל המפיצים'
    print(f"  {total_lbl}")
    print(SEP)
    for col, label in [
        ('feb_sales_mtd_pallets',    'מכירות פבר׳ MTD:               '),
        ('forecast_passover_pallets','ביקוש חזוי לפסח (18 ימים):     '),
        ('net_production_pallets',   'ייצור נדרש כשל"פ (מעוגל למשטח):'),
    ]:
        v = df[col].sum()
        print(f"  {label}  {v:>7.1f} משטחים  ({p2u(v):>8,} יח׳)")
    print(SEP)


def print_product_rollup(df: pd.DataFrame) -> None:
    summary = (
        df.groupby('product')[['forecast_passover_pallets', 'net_production_pallets']]
        .sum()
        .reset_index()
        .sort_values('net_production_pallets', ascending=False)
        .rename(columns={
            'product':                    'מוצר',
            'forecast_passover_pallets':  'ביקוש (מש׳)',
            'net_production_pallets':     'ייצור נדרש (מש׳)',
        })
    )
    summary['ייצור נדרש (יח׳)'] = summary['ייצור נדרש (מש׳)'].apply(p2u)
    print(summary.to_string(index=False))


# ─────────────────────────────────────────────────────────────────────────────
# 10. MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * W)
    print("  תוכנית ייצור לפסח — גלידת חלבון (דני אבדיה / Turbo)")
    print("  Passover Production Plan — Protein Ice Cream")
    print("=" * W)
    cap_str = (f"{DAILY_CAPACITY_PALLETS} מש׳/יום ({DAILY_CAPACITY_PALLETS * PALLET_SIZE:,} יח׳)"
               if DAILY_CAPACITY_PALLETS else "לא הוגדרה")
    print(f"\n  תחילת ייצור כשל\"פ:     {PRODUCTION_START_DATE.strftime('%d/%m/%Y')}")
    print(f"  חלון מכירות פסח:       {PASSOVER_SALES_START.strftime('%d/%m/%Y')} – {PASSOVER_SALES_END.strftime('%d/%m/%Y')}  ({PASSOVER_SALES_DAYS} ימים)")
    print(f"  ימי עבודה בשבוע:       {PRODUCTION_DAYS_PER_WEEK} (א׳–ו׳)")
    print(f"  קיבולת יומית:          {cap_str}")
    print(f"  גודל משטח:             {PALLET_SIZE:,} יחידות")
    print(f"  מלאי קיים מקוזז:       לא — אין תווית כשל\"פ")
    print(f"  מלאי ביטחון פסח:       0 — לא רוצים יתרות אחרי {PASSOVER_SALES_END.strftime('%d/%m/%Y')}")
    print()

    # ── Load ─────────────────────────────────────────────────────────────────
    feb_sales, warehouse_inv, dist_inv, _ = load_data()

    # ── Inventory context (informational only) ────────────────────────────────
    section("מלאי קיים — לידיעה בלבד (לא מקוזז) / Current Inventory — Context Only")
    print_inventory_context(warehouse_inv, dist_inv)

    # ── Forecast ──────────────────────────────────────────────────────────────
    section("שלב א׳: ביקוש חזוי לחלון מכירות פסח / Passover Sales Window Forecast")
    forecast_df = build_forecast(feb_sales, DISTRIBUTOR_PARAMS)
    result_df   = compute_net_requirements(forecast_df, DISTRIBUTOR_PARAMS)

    print_forecast_table(result_df)
    print_totals(result_df)

    # ── Product rollup ────────────────────────────────────────────────────────
    section("סיכום לפי מוצר / Product Rollup")
    print_product_rollup(result_df)

    # ── Schedule ──────────────────────────────────────────────────────────────
    section("שלב ב׳: לוח ייצור / Production Schedule")
    schedule_df, capacity_df = build_production_schedule(
        result_df,
        production_start        = PRODUCTION_START_DATE,
        deadline                = PRODUCTION_DEADLINE,
        daily_capacity_pallets  = DAILY_CAPACITY_PALLETS,
        days_per_week           = PRODUCTION_DAYS_PER_WEEK,
    )

    print("\n  היתכנות קיבולת / Capacity Feasibility:")
    print(SEP)
    print(capacity_df.to_string(index=False))

    if schedule_df is not None and not schedule_df.empty:
        print("\n  לוח ייצור מפורט / Full Production Schedule:")
        print(SEP)
        print(schedule_df.to_string(index=False))

        # סיכום יומי
        by_day = (
            schedule_df.groupby(['תאריך', 'יום'])['משטחים']
            .sum()
            .reset_index()
        )
        print("\n  סיכום יומי:")
        print(by_day.to_string(index=False))
        last_prod_date = schedule_df['תאריך'].iloc[-1]
        print(f"\n  ✓ הייצור הכשל\"פ מסתיים ב-{last_prod_date}")

    # ── Executive summary ─────────────────────────────────────────────────────
    section("סיכום מנהלים / Executive Summary")
    total_forecast_p = result_df['forecast_passover_pallets'].sum()
    total_req_p      = result_df['net_production_pallets'].sum()

    print(f"  ביקוש חזוי פסח (18 ימים):     {total_forecast_p:>6.1f} משטחים  ({p2u(total_forecast_p):>7,} יח׳)")
    print(f"  ייצור נדרש כשל\"פ:              {total_req_p:>6.1f} משטחים  ({p2u(total_req_p):>7,} יח׳)")
    print()

    if DAILY_CAPACITY_PALLETS:
        days_needed = math.ceil(total_req_p / DAILY_CAPACITY_PALLETS)
        finish_date = get_working_days(PRODUCTION_START_DATE, PRODUCTION_DEADLINE, PRODUCTION_DAYS_PER_WEEK)
        finish      = finish_date[days_needed - 1].strftime('%d/%m/%Y') if days_needed <= len(finish_date) else '?'
        print(f"  ימי ייצור נדרשים:              {days_needed} ימים")
        print(f"  צפי סיום ייצור:                {finish}")
        print(f"  חלון מכירות:                   {PASSOVER_SALES_START.strftime('%d/%m/%Y')} – {PASSOVER_SALES_END.strftime('%d/%m/%Y')}")

    print()
    print(SEP2)
    print("  הנחות עבודה:")
    print("  • מעיין נציגויות ואייסדרים רוכשים ישירות מהיצרן החל מתוכנית פסח.")
    print("  • המלאי הקיים אינו כשל\"פ — לא מקוזז מהביקוש.")
    print("  • ייצור מחושב בדיוק לחלון 9.3–26.3 בלי מלאי ביטחון — למינימום יתרות אחרי החג.")
    print(SEP2)
    print()

    return result_df, schedule_df, capacity_df


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    result_df, schedule_df, capacity_df = main()
