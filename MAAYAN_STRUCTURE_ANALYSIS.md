# Maayan Excel Files - Structure Analysis Report

## File Information
- **Primary File Analyzed**: Mayyan_Turbo.xlsx
- **Sheet Name**: טבלת ציר (Pivot Table)
- **Max Rows**: 1,070
- **Analysis Date**: February 22, 2026

---

## Column Structure (A through J)

| Column | Hebrew Name | English Translation | Data Type | Note |
|--------|------------|-------------------|-----------|------|
| A | סוג לקוח | Customer Type | Category | Main grouping: נוחות (Noodles), שוק פרטי (Private Market) |
| B | שם רשת | Chain/Network Name | Hierarchy | Sub-grouping: דור אלון, etc. |
| C | שם חשבון | Account Name | Text | Specific store/location with sub-customer markers |
| D | כתובת בחשבון | Account Address | Text | Full address of the location |
| E | עיר | City | Text | City/Region name |
| **F** | **שם פריט** | **Product/Item Name** | **[EMPTY]** | **See detailed analysis below** |
| G | נובמבר | November | Numeric | Sales quantity (2025) |
| H | דצמבר | December | Numeric | Sales quantity (2025) |
| I | ינואר | January | Numeric | Sales quantity (2026) |
| J | [Summary] | [Summary] | Numeric | Monthly/Total calculations |

---

## Column F (שם פריט) - DETAILED FINDINGS

### Status
- **Is Column F populated?**: NO - Column F contains NO data values
- **Why it exists**: Template structure for potential product-level breakdown
- **Current aggregation level**: Account level (Column C)

### Key Implication
The Maayan_Turbo.xlsx file provides **account-level sales data**, not product-level breakdowns. All quantities in columns G, H, I are aggregated per account location.

---

## Hierarchical Customer Breakdown

### Main Customer Types (Column A)
1. **נוחות** (Noodles/Convenience)
   - Primary category for ice cream sales
   
2. **שוק פרטי** (Private/Retail Market)
   - Alternative distribution channel

3. **סה"כ לדו"ח** (Report Total)
   - Summary row

---

## Sub-Customer Analysis (Column C - Account Names)

### Under דור אלון (Dor Alon) - Convenience Network
The data contains 132 דור אלון entries with three distinct sub-customer types:

#### 1. AM:PM Sub-Stores (60 occurrences)
Format: `דור אלון (AM:PM) [Location Name] [Code]`

**Examples**:
- דור אלון (AM:PM) סלוניקי 566
- דור אלון (AM:PM) אבא הלל 564
- דור אלון AM:PM הנשיא הרצליה פיתוח 545
- דור אלון (AM:PM) כלבו שלום 512
- דור אלון (AM:PM) הוד השרון 549
- דור אלון (AM:PM) בוגרשוב 534

**Characteristics**:
- AM:PM branded convenience stores
- 60 separate store locations
- Full historical data (November 2025 - January 2026)

#### 2. אלונית (Alonit) - Roadside/Kiosk Locations (68 occurrences)
Format: `דור אלון-אלונית [Location Name] [Code]`

**Examples**:
- דור אלון-אלונית מגל מזרח 948 (צפון)
- דור אלון-אלונית גשר הזיו 648
- דור אלון-אלונית יקום 955
- דור אלון-אלונית לטרון 935
- דור אלון-אלונית ערד 949
- דור אלון-אלונית צפת 913

**Characteristics**:
- Roadside/gas station kiosks
- 68 separate locations
- Scattered throughout Israel (north, south, east, west regions)

#### 3. סופר אלונית (Super Alonit) - Premium Kiosk Version (8 occurrences identified)
Format: `דור אלון- סופר אלונית [Location Name] [Code]` or `דור אלון-סופר אלונית [Location Name] [Code]`

**Examples**:
- דור אלון- סופר אלונית משמר השרון 655
- דור אלון- סופר אלונית עין-שמר 656
- דור אלון- סופר אלונית דוכן צמח 824
- דור אלון-סופר אלונית עינת 657
- דור אלון-סופר אלונית מושב נהלל 724

**Characteristics**:
- Premium/larger roadside kiosk format
- Fewer locations than regular אלונית
- Strategic locations

#### 4. דוכן (Dukan/Standalone Kiosk) - Minimal presence
Examples:
- דור אלון-דוכן גן שמואל 733

---

### שוק פרטי (Private/Retail Market)
Search findings indicate **1 occurrence** in the main file of שוק פרטי.

Row 377 example:
- Account: י.ד.עידה בע"מ ^ (לקוח)
- Address: אבן יהודה אזור תעשיה מערב קדימה

**Note**: In the earlier mayyan_feb_mtd.xlsx file (v1), טיב טעם (Tiv Taam) was found under שוק פרטי:
- טיב טעם - רעננה - דלי 051
- טיב טעם - אשדוד (ET)
- 33 total occurrences of טיב טעם in that file

---

## Special Sub-Customers - Search Results

### פז (Paz) Gas Station Network
- **פז ילו** (Paz Yilu): 1 occurrence found
  - Row 134: ילו- גשר האר"י 256
  - Associated with דור אלון distribution
  
- **פז סופר יודה** (Paz Super Yudah): 0 occurrences in current file

---

## Data Aggregation

### Current Aggregation Level
- **By**: Account Name (Column C) + Location (Column D)
- **NOT by**: Product type (Column F is empty)

### Available Metrics
- Monthly sales quantities (November 2025, December 2025, January 2026)
- No price/revenue data
- No product SKU breakdown
- No promotional data

---

## Summary of Findings

### Column F (שם פריט) Status
| Question | Answer |
|----------|--------|
| Is Column F used? | No |
| Why does it exist? | Template for future product-level granularity |
| Can we see product-level breakdown? | Not in current dataset |
| What level of aggregation do we have? | Account/Location level |

### Key Customer Structures Identified
1. **דור אלון (Dor Alon)** - 132 accounts across 3 sub-types:
   - AM:PM (60 locations)
   - אלונית (68 locations)
   - סופר אלונית (8 locations)
   
2. **שוק פרטי (Private Market)** - Limited in main file
   - May have more detail in alternative files

3. **פז (Paz)** - Minimal presence
   - Only אלונית variant (יילו) found

---

## File Variations
- **mayyan_feb_mtd.xlsx** - Earlier version with more detail on טיב טעם
- **maayan_feb_mtd_v2.xlsx** - Update/revision
- **Mayyan_Turbo.xlsx** - Current primary file (analyzed)

---

## Recommendations for Data Processing

1. **For דור אלון Analysis**:
   - Aggregate by sub-type (AM:PM vs אלונית vs סופר אלונית)
   - Parse location codes from account names
   
2. **For שוק פרטי Analysis**:
   - Check alternative files for more detail
   - Look for טיב טעם breakdown
   
3. **For Product-Level Analysis**:
   - Column F is not populated in current files
   - May need to request additional data source
   - Consider whether account-level aggregation is sufficient

