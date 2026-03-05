# Briefing — Session 2 Update Log
**Date:** March 4, 2026  
**Dashboard version:** v10 (final)

---

## What was done this session

### 1. New source files (complete February 2026)
Two new files were uploaded on Mar 4, replacing previous partial/MTD Feb data:

| File | Location | Content |
|---|---|---|
| `ice_feb_full.xlsx` | `data/icedreams/` | Complete Feb 2026 — Icedreams report by chain (`פברואר לפי רשתות`) |
| `maay_feb_full.xlsx` | `data/mayyan/` | Complete Feb 2026 — Mayyan detail distribution report |

**Key insight about icedream Feb file format:**  
The file title says "מכירות לעוגיפלצת חודשי לפי רשתות" — "עוגיפלצת" here refers to the **product brand**, not the customer. Each block is `סה"כ עוגיפלצת` + col2 = customer name. When col2 is None → the customer IS "עוגיפלצת" (the store chain).

---

### 2. February data changes (old MTD → new complete)

| Customer | Old Feb Units | New Feb Units | Δ |
|---|---|---|---|
| AMPM | 10,010 | 11,038 | +1,028 |
| אלונית | 469 | 1,728 | +1,259 |
| דלק | 680 | 998 | +318 |
| טיב טעם | 450 | 1,600 | +1,150 |
| שוק פרטי | 15,860 | 19,540 | +3,680 |
| פז יילו | 4,325 | 6,555 | +2,230 |
| פז סופר יודה | 1,290 | 1,840 | +550 |
| סונול | 378 | 478 | +100 |
| וולט מרקט | 6,947 | 9,685 | +2,738 |
| ינגו דלי | 736 | 1,046 | +310 |
| כרמלה | 0 | 105 | +105 |
| עוגיפלצת | 72 | 1,582 | +1,510 |
| חוות נעמי | 346 | 595 | +249 |
| גוד פארם | 332 | **0** | −332 (returns only in complete Feb) |
| נוי השדה | 110 | **0** | −110 (no Feb sales in complete file) |
| דומינוס | 410 | **0** | −410 (no Feb sales in complete file) |

**Total Feb Revenue:** ₪845,616 (MTD) → **₪1,063,273 (complete)**

---

### 3. Files updated

| File | Version | Notes |
|---|---|---|
| `Ice Cream Sales Dashboard.xlsx` | v10 | CP + PM + Summary tabs updated |
| `Sales Dashboard - Ice Cream.html` | — | customers[] + productMix[] + all MTD labels |

All "Feb MTD" labels changed to "Feb Complete Month" / "Feb '26" throughout HTML and xlsx.

---

### 4. Methodology used (for future updates)

**CP tab update:**
- Col 7 (Feb Revenue) + Col 11 (Feb Units) set directly from parsed source files
- Col 8 (Total Rev) + Col 12 (Total Units) = Dec + Jan + new Feb
- Mayyan revenue = units × ₪13.8 (flat)
- Icedreams revenue = actual invoice values, **excluding magadat** (triple pack)

**PM tab update — delta approach:**
```
old_Feb_flavor = max(0, PM_flavor - dec_raw_flavor - jan_raw_flavor)
new_PM_flavor  = old_PM_flavor - old_Feb_flavor + new_Feb_flavor
# Then scaled proportionally so PM total = CP total (exact match)
```

**CP vs PM reconciliation:** All 16 customers match exactly (±0 units) ✓

---

### 5. Sub-brand split rules (Mayyan)

| Chain in file | Dashboard customer | Condition |
|---|---|---|
| דור אלון | **אלונית** | if `'אלונית'` in account name |
| דור אלון | **AMPM** | otherwise |
| שוק פרטי | **טיב טעם** | if `'טיב טעם'` in account name |
| שוק פרטי | **שוק פרטי** | otherwise |

---

### 6. Current state of source files

| Month | Icedreams | Mayyan |
|---|---|---|
| December 2025 | `ICEDREAM- DECEMBER.xlsx` | `Mayyan_Turbo.xlsx` (multi-month) |
| January 2026 | `icedream - January.xlsx` (individual branches) | `Mayyan_Turbo.xlsx` |
| **February 2026** | **`ice_feb_full.xlsx`** ← USE THIS | **`maay_feb_full.xlsx`** ← USE THIS |

> ⚠️ Old partial Feb files (`~ice dream - feb 2.xlsx`, etc.) are superseded — do NOT use.

---

### 7. Scripts available

All parsing scripts are in `data/scripts/`:
- `parsers.py` — `parse_icedreams_file()`, `parse_mayyan_file()`
- Customer consolidation: branch names in Jan icedreams file map to top-level customers via keyword matching (e.g., `'גוד פארם *'` → `'גוד פארם'`)

---

### 8. Known data quality notes

- **דלק Jan**: CP shows 1,504 (corrected), raw Mayyan parse gives 1,524 — 20-unit correction applied historically
- **טיב טעם Jan**: CP shows 944 (corrected), raw Mayyan parse gives 1,118 — 174-unit correction applied historically  
  *(Both corrections sum to correct chain totals — likely reclassification between branches)*
- **גוד פארם**: Active Jan only (Dec=0, Feb=0 — returns in Feb). Total = 1,128 units (Jan only)
- **magadat** (triple pack `11553`) — **excluded** from CP units/revenue and PM tab. Tracked separately in icedreams parse output only.

