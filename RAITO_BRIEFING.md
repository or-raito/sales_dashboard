# Raito Project Briefing

Upload this file at the start of every new conversation about Raito data/dashboards.

---

## Company Overview

**Raito** — Israeli consumer goods company selling frozen products through two distributors. Expanding into additional categories in 2026.

### Brands

| Brand Key | Brand Name | Category | Status | Launch Date | Creator |
|---|---|---|---|---|---|
| turbo | Turbo by Deni Avdija | Ice Cream | Active | Dec 2025 | דני אבדיה |
| danis | Dani's Dream Cake | Frozen Cakes | Active | Dec 2025 | דניאל עמית |
| turbo_nuts | Turbo by Deni Avdija | Protein Snacks | Planned | Apr 2026 | דני אבדיה |
| ahlan | Ahlan | Coffee | Planned | Jul 2026 | Ma Kashur |
| w | W | Beverage Capsules | Planned | Aug 2026 | The Cohen |

### Active Products

| Product Key | Barcode | Full Name | Brand | Status | Prod. Cost (₪) | Units/Carton | Units/Pallet | Shelf Life | Storage |
|---|---|---|---|---|---|---|---|---|---|
| chocolate | 7290020531032 | Turbo Chocolate | turbo | Active | 6.5 | 10 | 2,400 | 12 months | -25°C |
| vanilla | 7290020531025 | Turbo Vanilla | turbo | Active | 6.5 | 10 | 2,400 | 12 months | -25°C |
| mango | 7290020531018 | Turbo Mango | turbo | Active | 6.5 | 10 | 2,400 | 12 months | -25°C |
| pistachio | — | Turbo Pistachio | turbo | New (Feb 2026) | 7.1 | 10 | 2,400 | 12 months | -25°C |
| dream_cake | — | Dani's Dream Cake | danis | Active | 53.5 | 3 | — | 3 months | -18°C |
| magadat | — | Turbo Magadat | turbo | Discontinued | — | — | — | — | -25°C |

### Planned Products

| SKU Key | Name | Brand | Target Launch |
|---|---|---|---|
| cake_sku2 | Dani's Cake SKU 2 | danis | May 2026 |
| cake_sku3 | Dani's Cake SKU 3 | danis | TBD |
| nuts_sku1 | Turbo Nuts SKU 1 | turbo_nuts | Apr 2026 |
| nuts_sku2 | Turbo Nuts SKU 2 | turbo_nuts | Apr 2026 |
| ahlan_sku1 | Ahlan Coffee SKU 1 | ahlan | Jul 2026 |
| w_sku1 | W Capsule SKU 1 | w | Aug 2026 |

**Icedream SKU names (the only 7 counted):**
- דרים קייק- 3 יח'
- טורבו מארז גלידות 250 מל * 3 יח'*סגור קבוע*
- טורבו- גלידת וניל מדגסקר 250 מל * 6 יח'
- טורבו- גלידת מנגו מאיה 250 מל * 10 יח'
- טורבו- גלידת מנגו מאיה 250 מל * 6 יח'
- טורבו- גלידת פיסטוק 250 * 10 יח'
- טורבו- גלידת שוקולד אגוזי לוז 250 * 10 יח'

**Excluded products:** באגסו (שוקולד לבן), שוקולד דובאי — not Raito products. magadat (triple pack barcode 11553) excluded from CP units/revenue, tracked separately.

### Manufacturers

| Manufacturer | Products | Status |
|---|---|---|
| Vaniglia | Turbo Ice Cream (chocolate, vanilla, mango, pistachio) | Active |
| Piece of Cake | Dani's Dream Cake | Active (transitioning out) |
| Biscotti | Dani's Dream Cake | New manufacturer from 1.3.2026 |
| Din Shiwuk | Turbo Nuts | Planned |
| Rajuan | Ahlan Coffee | Planned |

### B2B Pricing

B2B prices vary per customer. Source of truth: `data/price data/price db - 24.2.xlsx` (70 rows, 18 unique customers, 5 products).

**Dashboard fixed averages (Ma'ayan revenue estimates):**
- Ice cream flavors: ₪13.8/unit
- Dream Cake: ₪81.1/unit

Ma'ayan reports don't include revenue — calculated as units × price above.
Icedream reports include actual invoice values.

### Distributors

| Key       | Name              | Commission | Report Format |
|-----------|-------------------|------------|---------------|
| icedreams | Icedream          | 15% | Excel: bold customer headers, items in col D, qty in col F. Negative qty = sales, positive qty = returns. |
| mayyan    | Ma'ayan (מעיין נציגויות) | 25% | Excel: columns חודש (or שבועי)/פריט/בודדים/רשת/שם חשבון. Negative values = returns (handled by pandas sum). |

**Critical: Icedream returns handling** — The parser flips signs: negative raw values become positive sales, positive raw values become negative (returns). Uses `sign * -1` logic, NOT `abs()`.

### Warehouse & Logistics

- **Cold Storage:** Karfree (קרפריי) — PDF inventory reports with reversed Hebrew text
- **Dream Cake** is NOT stored at Karfree — goes direct to distributors
- **Pallet Calculation:** `round(units / 2400, 1)` — applies to ice cream only (10 units/carton × 240 cartons/pallet). Dream Cake shows "-"
- **Target Stock:** 1 month of average sales

---

## Sub-Brand Split Rules (Ma'ayan)

Ma'ayan data has two relevant columns: `שם רשת` (chain) and `שם חשבון` (account/branch). Splits are applied at the account level:

| Chain in file (שם רשת) | Dashboard customer | Condition |
|---|---|---|
| דור אלון | **AMPM** | `'AM:PM'` in account name |
| דור אלון | **אלונית** | `'אלונית'` in account name |
| דור אלון | **דור אלון** | all other (e.g., דוכן — very small) |
| שוק פרטי | **טיב טעם** | `'טיב טעם'` in account name |
| שוק פרטי | **שוק פרטי** | otherwise |
| פז יילו / פז ילו | **פז ילו** | normalized (Feb file uses יילו, Dec/Jan uses ילו) |

**Additional chain normalizations (Icedream + Ma'ayan):**
- All וולט / וואלט / וולט מרקט variants → **וולט מרקט**
- דומינוס פיצה → **דומינוס**

These rules are implemented in `config.py → extract_chain_name(customer_name, source_chain=None)`.

---

## Data Structure

### Folder Layout (in project directory)

```
data/
  icedreams/       ← Icedream monthly/weekly sales reports (.xlsx)
  mayyan/          ← Ma'ayan monthly/weekly sales reports (.xlsx)
  karfree/         ← Karfree warehouse inventory reports (.pdf)
  price data/      ← B2B price DB per customer (.xlsx)
  production/      ← Production data (future)

icedream/          ← Icedream stock/inventory snapshots (.xlsx)
Maayan/            ← Ma'ayan stock/inventory snapshots (.xlsx)

Raito_Master_Data.xlsx  ← Master data: brands, SKUs, manufacturers, distributors, logistics, pricing, config
```

### Current Source Files

| Month | Icedream Sales | Ma'ayan Sales |
|---|---|---|
| December 2025 | `data/icedreams/ICEDREAM- DECEMBER.xlsx` | `data/mayyan/Mayyan_Turbo.xlsx` (multi-month, monthly format with חודש column) |
| January 2026 | `data/icedreams/icedream - January.xlsx` (individual branches, 573 rows) | `data/mayyan/Mayyan_Turbo.xlsx` |
| **February 2026** | **`data/icedreams/ice_feb_full.xlsx`** | **`data/mayyan/maay_feb_full.xlsx`** (weekly format, no חודש column — uses שבועי) |

> ⚠️ Old partial Feb files are archived in `data/icedreams/_archive/`. Do NOT use.
> ⚠️ `icefream - January - CUSTOMERS .xlsx` was a duplicate — archived. Only `icedream - January.xlsx` should be used.

**Key insight about icedream Feb file format:**
The file title says "מכירות לעוגיפלצת חודשי לפי רשתות" — "עוגיפלצת" here refers to the **product brand**, not the customer. Each block is `סה"כ עוגיפלצת` + col2 = customer name. When col2 is None → the customer IS "עוגיפלצת" (the store chain).

### Inventory Files

| Location | File | Date |
|---|---|---|
| Karfree warehouse | `data/karfree/stock_4.3.pdf` | 04/03/2026 |
| Icedream distributor | `data/icedreams/icedream_stock_4:1.xlsx` | 4/3/2026 |
| Ma'ayan distributor | `data/mayyan/maayan_stock_4:3` (no extension) | 4/3/2026 |

### Naming Convention (preferred for new files)

- `icedream_sales_FEB26.xlsx`
- `maayan_sales_FEB26.xlsx`
- `karfree_stock_23FEB26.pdf`

Avoid: Hebrew filenames, spaces, missing extensions, date formats like `19:2`.

---

## Code Architecture

All scripts in `scripts/` directory:

| File | Role |
|---|---|
| `config.py` | Constants, pricing, product definitions, `classify_product()`, `extract_chain_name()`, `extract_units_per_carton()` |
| `parsers.py` | All file parsers (Icedream, Ma'ayan, Karfree, distributor stock) + `consolidate_data()` |
| `dashboard.py` | HTML dashboard generator → `docs/dashboard.html` |
| `excel_report.py` | Excel summary generator → `docs/supply_chain_summary.xlsx` |
| `excel_dashboard.py` | Full Excel dashboard → `docs/Raito_Business_Overview.xlsx` |
| `process_data.py` | Main orchestrator — run this to regenerate HTML + Excel summary |

### Key Functions

**config.py:**
- `classify_product(name)` — Hebrew SKU name → product key. Excludes באגסו and דובאי.
- `extract_chain_name(customer_name, source_chain=None)` — Branch name → chain name with all splits/normalizations. `source_chain` is used for Ma'ayan accounts to fall back to chain name when account doesn't match patterns.
- `extract_units_per_carton(name)` — Extracts multiplier from SKU name (e.g., "* 10 יח'" → 10)

**parsers.py:**
- `parse_icedreams_file(filepath)` — Returns `{month: {totals, by_customer}}`. Returns handling: `sign * -1`.
- `parse_mayyan_file(filepath)` — Returns `{month: {totals, by_chain, by_account, by_customer_type, branches}}`. Supports both monthly (חודש) and weekly (שבועי) formats.
- `consolidate_data()` — Merges all sources, computes `mayyan_accounts_revenue` with (chain, account) tuple keys.

### Running

```bash
# Regenerate HTML dashboard + Excel summary
python3 scripts/process_data.py

# Regenerate Excel dashboard only
python3 scripts/excel_dashboard.py
```

### Outputs

| File | Description |
|---|---|
| `docs/dashboard.html` | Interactive HTML dashboard with month/brand filters |
| `docs/supply_chain_summary.xlsx` | Excel summary report |
| `docs/Raito_Business_Overview.xlsx` | Full Excel dashboard (6 sheets: Overview, Detailed Sales, Icedream Customers, Ma'ayan Chains, Inventory, Top Customers) |

---

## Dashboard Sections

**Name:** Raito Business Overview

**Filters:** Period (Overview / Dec / Jan / Feb) × Brand (All Brands / Turbo / Dani's)

**Sections per view:**
1. **KPIs** — Total revenue, units, points of sale, creators, supply chain
2. **Revenue/Units Charts** — SVG bar charts (overview only)
3. **Detailed Summary** — Product × Month table with Ma'ayan/Icedream split
4. **Icedream Customers** — Aggregated by chain (via `extract_chain_name`)
5. **Ma'ayan Chains** — Aggregated by chain from account-level data (with splits)
6. **Top Customers** — Combined ranking from both distributors
7. **Inventory** (overview only) — Total stock, Karfree production planning, distributor inventory

---

## Decisions Already Made

1. **November 2025 excluded** — pre-launch data, distorts averages
2. **Data starts December 2025** — official launch month
3. **Ma'ayan revenue** = units × B2B average price (no revenue in raw reports)
4. **Ma'ayan stock format** differs from Icedream: units are individual (not cartons × factor), `1/10` notation in product names
5. **Karfree PDF** uses reversed Hebrew (right-to-left rendering issue) — parser handles this
6. **Dashboard name:** "Raito Business Overview" (renamed from "Raito Dashboard")
7. **GitHub Pages:** repo `or-raito/raito-dashboard`, URL: `https://or-raito.github.io/raito-dashboard/`
8. **Returns counted correctly** — Icedream parser uses sign-flip logic, NOT abs()
9. **Branch aggregation** — All tables aggregate branches into chains via `extract_chain_name()`

---

## Current Data State (as of March 4, 2026)

### Sales

| Month | Total Units | Revenue (₪) | Ma'ayan | Icedream |
|---|---|---|---|---|
| Dec '25 | 83,753 | 1,559,374 | 61,739 | 22,014 |
| Jan '26 | 51,131 | 1,092,105 | 30,353 | 20,778 |
| Feb '26 | 58,331 | 1,084,381 | 43,777 | 14,554 |
| **Total** | **193,215** | **₪3,735,860** | **135,869** | **57,346** |

### Inventory Snapshot (04/03/2026)

| Location | Units |
|---|---|
| Karfree warehouse | 71,430 |
| Icedream distributor | 8,602 |
| Ma'ayan distributor | 14,130 |
| **Total** | **94,162** |

---

## Known Data Quality Notes

- **דלק Jan**: CP (Sales Dashboard) shows 1,504 (corrected), raw Ma'ayan parse gives 1,524 — 20-unit correction applied historically
- **טיב טעם Jan**: CP shows 944 (corrected), raw Ma'ayan parse gives 1,118 — 174-unit correction applied historically. Both corrections sum to correct chain totals — likely reclassification between branches.
- **גוד פארם**: Active Jan only (Dec=0, Feb=0 — returns in Feb). Total = 1,128 units (Jan only)
- **January duplicate**: Two files existed for January Icedream. `icefream - January - CUSTOMERS .xlsx` was identical to `icedream - January.xlsx` (20,778 each). CUSTOMERS file archived to prevent double-counting.
- **February partial files**: Multiple partial Feb files were uploaded before the complete ones. All archived in `_archive/` subfolder.
- **Upload file corruption**: Excel files uploaded via chat consistently become 0 bytes. Workaround: user places files directly in the workspace folder.

---

## Sales Dashboard (separate system)

A separate "Sales Dashboard - Ice Cream.html" exists with hardcoded customer data (19 customers). It uses CP (Customer Performance) and PM (Product Mix) tabs from `Ice Cream Sales Dashboard.xlsx`.

**CP tab methodology:**
- Revenue + Units set directly from parsed source files
- Ma'ayan revenue = units × ₪13.8 (flat)
- Icedream revenue = actual invoice values, excluding magadat

**PM tab methodology (delta approach):**
```
old_Feb_flavor = max(0, PM_flavor - dec_raw_flavor - jan_raw_flavor)
new_PM_flavor  = old_PM_flavor - old_Feb_flavor + new_Feb_flavor
# Then scaled proportionally so PM total = CP total (exact match)
```

The Raito Business Overview dashboard uses dynamic parsing (not hardcoded) and may show slightly different numbers due to rounding and whether magadat is included per customer.

---

## How to Start a New Conversation

Paste this at the beginning:

> I'm working on the Raito project. Briefing file attached.
> My task: [describe what you need]
> Relevant files are in the project folder.

---

## Weekly Reports Transition (planned)

Moving from monthly to weekly distributor reports. Ma'ayan Feb file already uses weekly format (שבועי column instead of חודש). Parser supports both formats — infers month from filename when no month column exists.
