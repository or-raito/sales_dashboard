# Customer-Centric Trade & Sales Dashboard
## Comprehensive Implementation Specification & Logic Guide

**Prepared by:** Senior Business Intelligence Consultant
**Source Schema:** `Category_Management_2026-01-15T1213.pdf` (Looker Export, Country: ISR)
**Date:** February 2026
**Classification:** Internal — Sales Strategy

---

## STEP 1: DATA STRUCTURE ANALYSIS

### 1.1 Confirmed Schema — Available Columns & Metrics

The source file is structured as a hierarchical category management report with the following confirmed dimensions and measures:

#### Product Dimensions (Hierarchy)

> **Note:** The fields marked *(Excel — to be ingested)* will be sourced from a separate Excel file that will be attached and ingested into the database. These are not present in the current PDF export.

| Field | Description | Source | Example Value |
|---|---|---|---|
| `Raw GTIN` | Product barcode / unique item identifier | PDF export | 07290020531001 |
| `Item Name` | SKU-level product name | PDF export | (Hebrew product names) |
| `Brand Name` | Brand the product belongs to | PDF export | Magnum, Milka, Tamara |
| `Production Price per Unit` | Cost of goods / manufacturing cost per unit | **Excel — to be ingested** | ₪8.50 |
| `Case Size` | Number of units per trade case/box | **Excel — to be ingested** | 12, 24, 6 |
| `Active / Disabled` | Whether the SKU is currently active in the range | **Excel — to be ingested** | Active / Disabled |

#### Customer Dimension
| Field | Description | Source |
|---|---|---|
| `Customer Name` | Name of the retail account / trade customer | **Excel — to be ingested** |
| `Price per Unit per Customer` | The specific selling price agreed with each customer for a given SKU — enables customer-level price differentiation analysis | **Excel — to be ingested** |

> **Design note:** `Customer Name` is a first-class dimension in this schema. It must join to the sales fact table on a `Customer_ID` key. `Price per Unit per Customer` is a **customer-SKU level metric** (not a global average), meaning the same product can have different negotiated prices across different customers. This is essential for margin bridge analysis.

#### Financial Metrics
| Field | Formula/Logic | Notes |
|---|---|---|
| `Total Revenue VAT 0` | Revenue excluding VAT (net price) | Primary revenue metric — used for margin calculations |
| `Total Revenue VAT 18%` | Revenue including 18% VAT (`Revenue VAT 0 × 1.18`) | Gross consumer-facing revenue; use for customer invoice reconciliation |
| `Pure Product Margin (PPM) %` | Gross margin before shrinkage adjustment | Baseline profitability |
| `PPM (incl. shrinkage)` | Absolute margin after shrinkage deduction | More accurate profitability |
| `PPM (incl. shrinkage) %` | Margin % after shrinkage | Use this as primary margin KPI |

#### Volume & Efficiency Metrics
| Field | Description |
|---|---|
| `Total Sold Units` | Unit sales volume |
| `Avg Price per Unit` | Revenue ÷ Units; proxy for price positioning |
| `Item Count` | Distinct SKU count stocked |
| `Total Units Shrinked` | Units lost to shrinkage/waste |

#### Time Dimensions
| Field | Granularity | Confirmed Values | Status |
|---|---|---|---|
| `Metric Month` | Monthly | Jan–Dec 2026 shown on axis | ✅ In use |
| `Metric Week of Year` | Weekly | Weeks 1, 2, 3 confirmed | ✅ In use |

---

### 1.2 Critical Schema Gap — The Customer Dimension

**Finding:** The source schema contains **no explicit Customer entity**. There is no `Customer Name`, `Customer ID`, `Channel`, `Store`, or `Region` field present in the export.

**Interpretation & Design Decision:**
In this trade/category management context, the **`Vendor` dimension is structurally the closest analog to a "Customer" entity** — it represents the business partner relationship being tracked (analogous to a retail account or trade customer). For dashboard design purposes:

- **For Phase 1 (current data):** `Vendor Name` will serve as the Customer identifier.
- **For Phase 2 (after data ingestion):** The separately ingested files are expected to provide true customer-level fields. The dashboard architecture below is designed to **slot these fields in without structural rework**.

**Recommended Customer Dimension Schema to ingest:**
```
Customer_ID         (unique key — join anchor)
Customer_Name       (e.g., retail chain name)
Customer_Group      (e.g., Supermarkets, Convenience, Pharma)
Region              (e.g., North, South, Tel Aviv Metro)
Sales_Rep           (assigned account manager)
Channel             (e.g., Modern Trade, Traditional Trade, e-Commerce)
Account_Tier        (e.g., A, B, C — strategic segmentation)
```

---

### 1.3 Comparative Metrics Feasibility

| Comparative Metric | Available? | Logic |
|---|---|---|
| Month-over-Month (MoM) | ✅ Yes | Monthly axis exists; calculate current vs. prior month |
| Year-over-Year (YoY) | ⚠️ Partial | Monthly axis shows 2026 only; YoY requires 2025 data from ingested files |
| Target vs. Actual | ❌ Not in source | Targets must be ingested as a separate `Budget` or `Target` table |
| Shrinkage Impact | ✅ Yes | Delta between PPM% and PPM (incl. shrinkage) % |
| Price vs. Volume Mix | ✅ Yes | Avg Price per Unit × Units sold decomposition |

---

## STEP 2: DASHBOARD STRATEGY — THE CUSTOMER-CENTRIC DIRECTIVE

### 2.1 Design Philosophy

The dashboard is built on a single organizing principle: **every metric must be answerable through the lens of the customer (trade account/vendor).** Product performance is secondary — it exists only to explain *why* a customer is performing the way they are.

This means:
- The **default landing view** loads at the customer/vendor level, not the category level.
- Drill-down goes **from customer → category → product**, not the reverse.
- All aggregates are **filterable and breakable by customer** as a first-class dimension.

### 2.2 Data Model — Recommended Star Schema

```
                    ┌──────────────────────────┐
                    │      DIM_CUSTOMER        │
                    │   (Excel — to ingest)    │
                    │  Customer_ID  (PK)       │
                    │  Customer_Name           │
                    │  Region                  │
                    │  Channel                 │
                    │  Account_Tier            │
                    │  Sales_Rep               │
                    └────────────┬─────────────┘
                                 │ join on Customer_ID
┌──────────────┐  ┌──────────────▼────────────────────────┐  ┌───────────────────────────┐
│  DIM_DATE    │  │            FACT_SALES                  │  │       DIM_PRODUCT         │
│  Month       ├──│  Date_Key (Month / Week)               │──│  GTIN           (PK)      │
│  Week        │  │  Customer_Key  ──► Customer_Name       │  │  Item_Name                │
└──────────────┘  │  Product_Key                           │  │  Brand_Name               │
                  │  Revenue_Vat0                          │  │  Manufacturer             │
                  │  Revenue_Vat18  (Vat0 × 1.18)         │  │  Hierarchy_L1             │
                  │  Price_Per_Unit_Per_Customer ◄─ Excel  │  │  Hierarchy_L2             │
                  │  PPM_Pct                               │  │  Hierarchy_L3             │
                  │  PPM_incl_Shrinkage                    │  │  Production_Cost_Per_Unit │◄─ Excel
                  │  PPM_Shrinkage_Pct                     │  │  Case_Size                │◄─ Excel
                  │  Units_Sold                            │  │  Active_Flag              │◄─ Excel
                  │  Units_Shrinked                        │  └───────────────────────────┘
                  │  Item_Count                            │
                  └───────────────────────────────────────┘
```

> **Fields marked ◄─ Excel** are ingested from the Excel master file and joined to the respective dimension table on `GTIN` (product) or `Customer_ID` (customer). All other fields flow from the PDF/Looker export.

---

## STEP 3: DETAILED DASHBOARD SPECIFICATION

---

## A. EXECUTIVE SUMMARY — TOP-LEVEL KPIs

These 6 KPIs appear as **cards at the top of every dashboard view**. All are aggregated at the global level by default and respond dynamically to any active filter, including Customer/Vendor selection.

---

### KPI 1 — Total Revenue (Excl. VAT)
- **Source field:** `SUM(Total Revenue Vat0)`
- **Format:** Currency (ILS / local currency), 0 decimal places, abbreviated (e.g., ₪531.9K)
- **Context indicator:** Trend sparkline showing last 4 weeks or last 3 months
- **Customer filter behavior:** When a customer is selected, shows that customer's revenue contribution. Secondary stat shows **% share of total portfolio** (e.g., "Vendor X = 20% of total revenue").

---

### KPI 2 — Portfolio Margin % (PPM incl. Shrinkage)
- **Source field:** `SUM(PPM incl. shrinkage) / SUM(Total Revenue Vat0)`
- **Format:** Percentage, 2 decimal places
- **Context indicator:** Color-coded RAG status (Red < 40%, Amber 40–45%, Green > 45%)
- **Customer filter behavior:** Shows selected customer's weighted average margin. Compare against portfolio benchmark with a delta label (e.g., "▼ 2.3pp below portfolio avg").

---

### KPI 3 — Total Units Sold
- **Source field:** `SUM(Total Sold Units)`
- **Format:** Integer, comma-separated (e.g., 27,810)
- **Context indicator:** MoM change % badge
- **Customer filter behavior:** Customer's unit volume + their share of total units (volume mix indicator).

---

### KPI 4 — Average Selling Price per Unit
- **Source field:** `SUM(Revenue Vat0) / SUM(Total Sold Units)`
- **Format:** Currency, 2 decimal places (e.g., ₪23.42)
- **Context indicator:** Trend arrow vs. prior period
- **Customer filter behavior:** Reveals pricing tier and whether a customer skews toward premium or value SKUs — critical for mix analysis.

---

### KPI 5 — Active SKU Count (Item Count)
- **Source field:** `COUNT(DISTINCT Raw GTIN)` where `Total Sold Units > 0`
- **Format:** Integer
- **Context indicator:** Delta vs. prior period (SKUs added/lost — range change indicator)
- **Customer filter behavior:** Shows assortment depth per customer. Wide delta vs. portfolio suggests range gaps or exclusive listings.

---

### KPI 6 — Shrinkage Impact (Revenue at Risk)
- **Source field:** `SUM(PPM) - SUM(PPM incl. shrinkage)` — expressed as currency loss
- **Format:** Currency with negative value flag (e.g., ₪-5,231 lost to shrinkage)
- **Context indicator:** % of gross PPM eroded by shrinkage
- **Customer filter behavior:** Identifies which customers have disproportionate shrinkage exposure — a direct profitability risk signal.

---

## B. THE CUSTOMER DEEP-DIVE — MAIN VIEW

The main view has three analytical panels, each answering a distinct strategic question.

---

### B.1 — WHO ARE THE TOP PERFORMERS?
**Visualization: Dual-axis Bar + Line (Pareto-style) — Top 15 Customers by Revenue**

**Chart type:** Horizontal bar chart (primary) with cumulative % line overlay (secondary axis)

**X-axis:** Customer / Vendor Name (sorted descending by Revenue)
**Primary bar (blue):** `Total Revenue Vat0` per customer
**Secondary bar or dot (orange):** `PPM incl. shrinkage %` per customer
**Line (grey, right axis):** Cumulative revenue % (Pareto 80/20 reference line at 80%)

**What this answers:**
- Which customers generate the most revenue?
- Is high revenue always matched by high margin? (Visual gap between bars reveals margin-revenue misalignment)
- The Pareto line shows how many customers account for 80% of total revenue — typically revealing concentration risk.

**Color logic on the margin dot/bar:**
- Green: PPM% > portfolio average (e.g., > 45.06%)
- Amber: Within ±2pp of portfolio average
- Red: More than 2pp below portfolio average

**Interaction:** Clicking a customer bar sets a global filter for all panels below.

---

### B.2 — WHO IS GROWING VS. DECLINING?
**Visualization: Scatter Plot — Revenue vs. YoY Growth (or MoM Growth if YoY data is unavailable)**

**X-axis:** `Total Revenue Vat0` (current period) — represents customer size/importance
**Y-axis:** `% Revenue Growth vs. Prior Period` (MoM or YoY depending on data availability)
**Bubble size:** `Total Sold Units` — indicates volume weight
**Bubble color:** `PPM (incl. shrinkage) %` — warm/cool color scale (red = low margin, green = high margin)
**Label:** Customer/Vendor Name on hover

**Quadrant Framework (reference lines at median X and Y=0%):**
| Quadrant | Label | Strategic Action |
|---|---|---|
| High Revenue, Positive Growth | ⭐ Stars — Protect & Invest | Prioritize, expand range |
| High Revenue, Negative Growth | ⚠️ At-Risk Champions | Urgent review, root cause analysis |
| Low Revenue, Positive Growth | 🚀 Emerging Accounts | Develop — potential future stars |
| Low Revenue, Negative Growth | 🔴 Declining Tail | Evaluate ROI; consider deprioritizing |

**Data logic note:** If only single-period data is available (as in the sample), this chart initially renders on a MoM basis using Week-over-Week trend from the weekly development data. YoY becomes available once 2025 data is ingested.

---

### B.3 — WHAT IS THE PRODUCT MIX PER CUSTOMER?
**Visualization: 100% Stacked Bar Chart — Category Mix by Customer**

**X-axis:** Top 10–15 Customers/Vendors (by revenue)
**Y-axis:** 0–100% (proportion of revenue)
**Segments (color-coded):** `Product Classification Hierarchy Level3` categories:
- Ice Cream & Ice Cream Tubs (blue)
- Frozen Desserts (purple)
- Ice Lollies (orange)
- Other (grey)

**What this answers:**
- Does each customer have a balanced category mix, or are they over-indexed on low-margin sub-categories?
- Which customers are strong in Ice Lollies (52.95% PPM — the highest margin sub-category)?
- Which customers rely heavily on Frozen Desserts (43.98% PPM — the lowest)?

**Secondary toggle — Brand Mix View:**
Replaces Level 3 categories with Brand segments (Top 10 brands by revenue). This reveals whether premium brands (e.g., פרנוי at ₪105K revenue) are concentrated in specific accounts.

**Interaction:** Clicking a segment filters the product-level table below to show only that category's SKUs for the selected customer.

---

### B.4 — SUPPLEMENTARY: CUSTOMER PERFORMANCE TABLE (Detailed Grid)

A sortable, searchable data table providing the full analytical record per customer.

| Column | Source | Notes |
|---|---|---|
| Customer / Vendor | `Vendor Name` | Clickable → drill to product detail |
| Total Revenue | `SUM(Revenue Vat0)` | Sortable |
| Revenue Share % | Customer Rev / Total Rev | Auto-calculated |
| PPM % (adj.) | `Weighted avg PPM incl. shrinkage %` | Color-coded RAG |
| Units Sold | `SUM(Total Sold Units)` | Sortable |
| Avg Price / Unit | `Revenue / Units` | Price tier indicator |
| Active SKUs | `COUNT DISTINCT GTIN where Units > 0` | |
| Shrinkage Units | `SUM(Total Units Shrinked)` | Risk flag if > 5% of units |
| Revenue Growth | `Current vs. Prior Period %` | ▲ / ▼ indicators |
| Top Category | `L3 with highest revenue share` | Quick-read mix summary |

**Row-level drill-down:** Expanding any customer row reveals a sub-table of their top 10 SKUs by revenue, with full margin and volume detail.

---

## C. FILTERS AND SLICERS

### C.1 Mandatory Filters

**Filter 1 — Customer / Vendor Name**
- **Type:** Multi-select dropdown with search
- **Source field:** `Vendor Name` (Phase 1); `Customer_Name` after data ingestion
- **Behavior:** Selecting one or more customers filters ALL panels simultaneously. A "Select All" toggle resets to portfolio view.
- **Visual indicator:** Active filter shown as a chip/badge in the dashboard header.

**Filter 2 — Time Period**
- **Type:** Date range picker with preset quick-select options
- **Presets:** This Month | Last 4 Weeks | Last 3 Months | YTD | Custom
- **Source fields:** `Metric Month`, `Metric Week of Year`
- **Behavior:** Controls the primary period. A secondary "Comparison Period" toggle activates delta calculations.

---

### C.2 Optional Filters (Schema-confirmed availability)

**Filter 3 — Product Category**
- **Type:** Cascading hierarchy selector (L1 → L2 → L3)
- **Purpose:** Narrow analysis to a specific category (e.g., "Show me Customer X's performance in Ice Lollies only")

**Filter 4 — Brand**
- **Type:** Multi-select dropdown (60+ brands available in schema)
- **Purpose:** Brand-level customer analysis (e.g., "Which accounts are driving Magnum growth?")

**Filter 5 — Manufacturer**
- **Type:** Multi-select dropdown (19 confirmed in schema)
- **Purpose:** Useful for manufacturer-specific account reviews

**Filter 6 — Vendor / Supplier Tier**
- **Type:** Single-select (derived from vendor revenue ranking)
- **Logic:** Top 5 vendors by revenue = Tier 1; Next 5 = Tier 2; Remainder = Tier 3
- **Purpose:** Strategic segmentation of trade customers without needing ingested CRM data

---

### C.3 Filters Pending Data Ingestion (Design reserved)

The filter bar includes **placeholder slots** for the following fields, which will activate once customer master data is ingested:

- **Region** (e.g., geographic territory — North / Central / South)
- **Channel** (e.g., Modern Trade / Traditional / e-Commerce)
- **Sales Representative / Account Manager**
- **Account Tier** (A / B / C — strategic priority classification)

---

## D. ACTIONABLE INSIGHTS — BUSINESS QUESTIONS THIS DASHBOARD ANSWERS

The following three questions are the primary use cases for a Sales Manager conducting a weekly or monthly business review.

---

### Business Question 1:
**"Which customers generate high revenue but deliver below-average margins — and what is causing the margin drag?"**

**How the dashboard answers it:**
- The Pareto chart (B.1) visually separates revenue leaders from margin leaders. Customers with tall revenue bars but red/amber margin dots are immediately identifiable as "volume traps."
- The Customer Detail Table (B.4) surfaces the `PPM% (adj.)` with RAG coloring for every account.
- Drilling into a flagged customer's product mix (B.3) reveals whether margin drag is structural (they over-index on inherently low-margin sub-categories like Frozen Desserts at 43.98%) or operational (driven by high shrinkage — identified via the Shrinkage Impact KPI).

**Actionable output:** The Sales Manager can walk into a customer negotiation knowing whether the issue is assortment mix, pricing, or operational shrinkage, and propose a targeted remedy.

---

### Business Question 2:
**"Which customers are growing their revenue but shrinking their basket — and are we at risk of losing range?"**

**How the dashboard answers it:**
- The Scatter Plot (B.2) highlights accounts in the "Positive Revenue Growth" quadrant.
- Cross-referencing with the `Active SKU Count` KPI and the Customer Table's "Active SKUs" column reveals if unit growth is driven by fewer, higher-value SKUs (concentration risk) or by genuine volume expansion across the range.
- A declining SKU count alongside revenue growth signals that a customer is de-listing products, which reduces future revenue resilience even as current numbers look healthy.

**Actionable output:** The Sales Manager can identify range rationalization risk early and engage the customer on assortment reinstatement before the next range review.

---

### Business Question 3:
**"Which emerging customers (currently small in revenue) show strong margin profiles and growth trends — and should receive increased investment?"**

**How the dashboard answers it:**
- The Scatter Plot (B.2) "Emerging Accounts" quadrant (Low Revenue, Positive Growth) surfaces these candidates.
- Filtering the Product Mix chart (B.3) to these accounts reveals whether they already carry premium brands (high-ASP, high-margin SKUs) — a leading indicator of a commercially sophisticated account.
- The `Avg Price per Unit` KPI for these accounts, compared against the portfolio benchmark of ₪23.42, shows whether they're premium-indexed.

**Actionable output:** The Sales Manager can build a prioritized list of "accounts to develop" with supporting data for budget allocation decisions, rather than relying on subjective relationship-based prioritization.

---

## APPENDIX 1: IMPLEMENTATION NOTES — DATA INGESTION REQUIREMENTS

When the separate operational data files are ingested, the following mappings must be confirmed:

| Dashboard Field | Expected Source Field | Join Key |
|---|---|---|
| Customer_Name | CRM / ERP Customer Master | Vendor_ID = Customer_ID |
| Region | Customer Master | Customer_ID |
| Sales_Rep | CRM Account Assignment | Customer_ID |
| Channel | Customer Master | Customer_ID |
| YoY Revenue | Prior year fact table | Date + Customer_ID + Product_ID |
| Budget / Target | Planning/Budget file | Month + Customer_ID + Category |

---

## APPENDIX 2: RECOMMENDED KPI BENCHMARKS (Based on Sample Data)

These benchmarks are derived from the sample schema and should be validated against the full operational dataset after ingestion:

| Metric | Sample Value | Suggested Benchmark Threshold |
|---|---|---|
| Portfolio PPM % (incl. shrinkage) | 45.06% | Alert if any customer < 40% |
| Avg Price per Unit | ₪23.42 | Flag accounts < ₪15 (value-skewed) |
| Highest Margin Sub-category | Ice Lollies — 52.95% | Use as mix-shift target |
| Lowest Margin Sub-category | Frozen Desserts — 43.08% | Monitor share within each account |
| Shrinkage Rate | ~3.2% of units (896 of 27,810) | Alert if customer > 5% shrinkage rate |

---

## APPENDIX 3: PHASED BUILD PLAN

**Phase 1 — Foundation (Current Schema Only)**
- Build all 6 KPI cards using Vendor as Customer proxy
- Build Pareto chart and Customer Detail Table
- Implement all confirmed filters (Category, Brand, Time, Vendor)
- Deliver: Working prototype with Vendor-level customer analytics

**Phase 2 — Post-Ingestion Enhancement**
- Join Customer Master data; replace Vendor with true Customer_Name
- Activate Region, Channel, Sales Rep, Account Tier filters
- Enable YoY comparisons once prior-year fact data is available
- Add Budget vs. Actual tracking once planning data is ingested
- Deliver: Full Customer-Centric operational dashboard

**Phase 3 — Advanced Analytics**
- Customer Lifetime Value (CLV) trend modeling
- Predictive churn risk scoring (declining accounts)
- Automated alert system: "Customer X dropped below 40% PPM this week"
- Deliver: Proactive insight layer on top of descriptive dashboard

---

*Document generated from schema analysis of `Category_Management_2026-01-15T1213.pdf`*
*Numerical values in this document are illustrative benchmarks derived from the sample file. Final KPIs and thresholds must be recalibrated against full operational data.*
