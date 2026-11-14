# World Order Monitor — Specification

**Goal:** a static website that places every country in the world on the cycles Ray Dalio describes in
*Principles for Dealing with the Changing World Order* (2021). It also draws on his annual Country Power /
Great Powers Index (2022–2024) and *How Countries Go Broke* (2025). Every number is computed from public
data and shown with its source and year, so each claim can be checked. The site can be rebuilt on a later
date by re-running one script and editing one curated file.

Research date of this edition: **2026-11-14**. It is printed in the site footer, along with the data vintage.

---

## 1. What Dalio's model actually is (from primary sources)

Sources read: *Country Power Index 2022* (economicprinciples.org, April 2022, 60 pp; gauge definitions on
pp. 54–57), the book's chapters 1–2, 5–6 and 14, *Great Powers Index 2024* (published scores), *How
Countries Go Broke* (2025), and Dalio's 2025–2026 essays and interviews (see `research/curated.json` → `sources`).

### 1.1 The three big cycles
| Cycle | Dalio's stages | How he measures it |
|---|---|---|
| **Big debt / money / economic cycle** | Sound money → debt build-up → bubble/top → deleveraging (defaults, or printing and devaluation) → crisis recedes and a new monetary order begins (*How Countries Go Broke*, ch. 2–4) | **Debt Burden** gauge: (a) debt vs. assets, (b) external and internal surpluses/deficits, (c) debt service vs. GDP, (d) own-currency vs. foreign-currency debt, (e) domestic vs. foreign holders, (f) credit rating. Reserve-currency status is deliberately left out of this gauge. **Expected Growth** gauge: 10-year real growth forecast, ⅔ weight on productivity drivers and ⅓ on the drag from debt. |
| **Internal order / disorder cycle** | 1 New order, leadership consolidates → 2 Resource-allocation systems and bureaucracies built → 3 Peace and prosperity → 4 Excesses: spending, debt, widening gaps → 5 Bad finances plus intense conflict → 6 Civil war / revolution (book ch. 5) | **Gaps in Wealth, Opportunity & Values** (top-1%/10% income shares, political polarisation) and **Internal Conflict** (protests, partisanship, discontent surveys) |
| **External order / disorder cycle** | Peace under a dominant power → rising challenger → trade/economic war → technology war → geopolitical war → capital war → military war → new order (book ch. 6) | External Conflict gauge, measured between pairs of countries against the hegemon (USA) or the rising power (CHN) |

### 1.2 The 18 determinants (Power Index 2022, p. 2)
- **Big cycles (5):** Debt Burden, Expected Growth, Gaps in Wealth/Opportunity/Values, Internal Conflict, External Order.
- **Eight key measures of power:** Education, Innovation & Technology, Cost Competitiveness, Military Strength, Trade, Economic Output, Markets & Financial Center, Reserve Currency Status.
- **Additional (5+):** Geology, Resource-Allocation Efficiency, Acts of Nature, Infrastructure & Investment, Character/Civility/Determination, Governance/Rule of Law.

**How Dalio aggregates:** each gauge is a composite of several statistics, mixing *absolute size* (e.g.
share of world exports) and *quality / per capita* (e.g. PISA, GDP per capita). Within a gauge he normalises
using z-scores across the 24 leading countries, or using a weighted average percent rank (0–100%) in the
appendix. The overall **Empire / Power score (0–1)** is "a roughly equal" weighting of the gauges. He also
shows a 20-year change arrow for every gauge. **He does not publish exact weights or the underlying
indicator list**, so any public replication is an approximation. This site says so openly and calibrates
against his published 2024 scores (§4).

**Archetypal sequence (book ch. 1):** a rising empire improves first in education, then innovation,
competitiveness, output and trade, then military, then financial center, and last in reserve currency, which
lags and is the last to fall. A country whose lagging strengths (financial center, reserve currency) clearly
exceed its leading strengths (education, innovation, competitiveness) is late in its cycle.

### 1.3 Dalio's own latest readings (curated, with citations)
- World/US: "we are now in … Stage 5, the stage that immediately precedes the breakdowns" (Fortune, 14 Mar 2026). He sees the US as possibly moving toward Stage 6 (Jan 2026). He wants the US deficit cut from about 7% to about 3% of GDP (*How Countries Go Broke*).
- China: at a "fork in the road" between a "beautiful deleveraging" and a Japan-style malaise. Its debts are mostly in its own currency and owed to its own citizens (2024–2025).
- UK: a "debt doom loop" / risk of a "debt death spiral" (Jan and Jul 2025).
- Japan: about 215% debt/GDP. Financial repression delays a crisis but hurts bondholders and the yen (Aug 2026).
- India: "best fundamentals", the highest 10-year growth outlook among major economies (Dec 2025).
- Published 2024 Great Powers Index scores for the 24 countries (US 0.89, CHN 0.80, EUR 0.56 … ARG 0.07). These are shown next to our computed score.

---

## 2. Data model (what is computed for every country)

Coverage: all ~200 countries in the World Bank API, plus a virtual **Eurozone** entity (21 members from
2026, aggregated). Each statistic stores `{value, year, source}`.

### 2.1 Gauges → public indicators
| Gauge | Size component (share of world) | Quality component (percent rank) | Source |
|---|---|---|---|
| Education | tertiary students (`SE.TER.ENRL`) | tertiary enrolment % (`SE.TER.ENRR`), harmonised test scores (`HD.HCI.HLOS`), Human Capital Index (`HD.HCI.OVRL`) | World Bank / UNESCO |
| Innovation & Technology | R&D spending US$ (`GB.XPD.RSDV.GD.ZS` × GDP), resident patents (`IP.PAT.RESD`) | R&D % GDP, researchers per million (`SP.POP.SCIE.RD.P6`), high-tech exports % | WB / UNESCO / WIPO |
| Cost Competitiveness | — (relative by nature) | output per worker (`SL.GDP.PCAP.EM.KD`) ÷ price level (`PA.NUS.PPPC.RF`), human capital ÷ price level | WB / ILO / ICP |
| Military Strength | military spending US$ (`MS.MIL.XPND.CD`), armed forces (`MS.MIL.TOTL.P1`), nuclear warheads | military spending % GDP | SIPRI via WB, FAS 2026 |
| Trade | exports of goods & services US$ (`NE.EXP.GNFS.CD`) | exports % GDP | WB |
| Economic Output | GDP PPP (`NY.GDP.MKTP.PP.CD`) | GDP per capita PPP | WB / IMF |
| Markets & Financial Center | stock market cap (`CM.MKT.LCAP.CD`), value traded | GFCI 40 (Sep 2026) best-ranked city | WB / WFE, Z/Yen |
| Reserve Currency Status | share of world FX reserves (IMF COFER Q2 2026) and of SWIFT payments (Jun 2026) | — | IMF, SWIFT |
| Debt Burden *(risk, high = bad)* | — | gov gross debt % GDP, private debt % GDP, interest % revenue, fiscal balance, current account, external debt % GNI, inflation | IMF WEO Oct 2026, IMF GDD, WB |
| Expected Growth | — | IMF real GDP growth forecast, average of the next 5 years (the WEO horizon; Dalio uses 10) | IMF WEO |
| Gaps in Wealth & Opportunity *(high = bad)* | — | Gini (`SI.POV.GINI`), top-10% income share (`SI.DST.10TH.10`) | WB PIP |
| Internal Conflict *(high = bad)* | — | Political Stability & Absence of Violence (WGI `PV.EST`, inverted), Voice & Accountability, active civil-war flag | WB WGI, curated |
| External Conflict | — | curated "war ladder" level (§3.3) | curated |
| Infrastructure & Investment | gross capital formation US$ | investment % GDP, savings % GDP, Logistics Performance Index | WB |
| Governance / Rule of Law | — | WGI Rule of Law, Control of Corruption, Government Effectiveness | WB WGI |
| Geology | land area, energy production | natural-resource rents % GDP, net energy imports (inverted) | WB / IEA |
| Resource-Allocation Efficiency | — | unemployment (inverted), private credit vs. GDP-per-capita growth | WB / IMF |
| Character / Civility / Determination | — | labour-force participation, gross savings rate | WB (proxy, rated so-so like Dalio's) |
| Acts of Nature | — | **not built**: no open, global, comparable series. Shown as "not measured" | — |

### 2.2 Normalisation and scoring
1. **Quality indicators:** percent rank (0–1) across all countries with data, with "bad" indicators inverted. This follows Dalio's appendix method.
2. **Size indicators:** `(share / max share)^p`. The exponent `p` (about 0.5) compresses the gap between giants and mid-sized powers.
3. **Gauge score** = `w·size + (1−w)·quality`, ignoring any component with missing data. A gauge needs at least one component.
4. **Power score (0–1)** = weighted mean of the 8 key measures and the "additional" gauges. `p`, `w` and the key/additional weight are **fitted to Dalio's published 2024 scores** for his 24 entities (least squares). The fit statistics (Pearson r, mean absolute error, rank correlation) are printed on the methodology section.
5. **20-year trend:** the same gauges are recomputed with each indicator's value nearest to 2006. Curated inputs use their 2005/2006 values (COFER 2005). The site shows the change as ▲/▼ for each gauge and for the total.
6. **Ranks:** given both among all countries and among Dalio's 24.

---

## 3. Cycle positions (the classification shown on the map)

Every country gets a computed position from the rules below. The ~25 major countries can carry a **curated
override** with a written rationale and Dalio quotes where they exist. The UI always shows which kind
(computed vs. curated) it is displaying.

### 3.1 Big debt cycle stage (1–5)
| Stage | Label | Rule |
|---|---|---|
| 1 | Sound money / low debt | debt-risk < 0.35 |
| 2 | Debt build-up | 0.35 – 0.6 |
| 3 | Top / late-cycle squeeze (debt service crowds out spending) | ≥ 0.6, or gov debt ≥ 100% GDP, or interest ≥ 15% of revenue |
| 4 | Deleveraging / crisis (default, restructuring, printing/devaluation) | curated default list, or inflation ≥ 40%, or interest ≥ 35% of revenue |
| 5 | Crisis recedes / new equilibrium | curated (completed restructuring and stabilisation) |

Debt-risk is the Debt Burden gauge: the mean percent rank of gov debt, private debt, interest/revenue,
deficit, current-account deficit, external debt and inflation.

### 3.2 Internal order stage (1–6)
| Stage | Rule (computed) |
|---|---|
| 6 Civil war / revolution | curated active civil-war list, or WGI political stability ≤ −2.0 |
| 1 New order consolidating | curated (regime change within ~3 years) |
| 5 Bad finances + intense conflict | internal-stress ≥ 0.6 and (debt stage ≥ 3 or political stability < −1) |
| 4 Excesses, widening gaps | internal-stress ≥ 0.45 |
| 3 Peace & prosperity / stable order | otherwise |
| 2 Systems being built | curated only |

Internal-stress = 0.4·gaps + 0.4·conflict + 0.2·debt-risk.

### 3.3 External order: Dalio's war ladder (0–5)
0 No major conflict · 1 Trade/economic war · 2 Technology war · 3 Geopolitical war (territorial or
proxy, alliance confrontation) · 4 Capital war (sanctions, asset freezes, cut-off from finance) ·
5 Military war. These levels are curated from current events as of the research date, with the
counterparties listed.

### 3.4 Position on the archetypal empire arc
A dot on Dalio's rise-peak-decline curve, derived from the power level, the 20-year power trend, and the
lagging-minus-leading gap. The leading gap uses Education, Innovation and Competitiveness. The lagging
gap uses Financial Center and Reserve Currency. Phases: **Rising · Near peak · Declining**.

---

## 4. Calibration and honesty rules
- Dalio's 2024 published score is shown beside our computed score for his 24 entities.
- Each gauge shows Dalio's reliability label (Reliable / So-so) from the 2022 report.
- Any value older than 5 years is flagged as stale.
- Curated judgments always link to a source. Computed classifications show the rule that fired.
- Disclaimer: this is an independent replication from public data, not Dalio's or Bridgewater's model.

---

## 5. Website

**Static:** `site/index.html` with vanilla JS, D3 v7 and topojson-client, all vendored. Data ships as
`site/data/data.js` (`window.WORLD_DATA`), so the page works from `file://` with no server.

1. **Header.** One-line thesis: "Where every country stands on Dalio's big cycles", plus a layer switcher
   for the map: Power score · Debt cycle · Internal order · External conflict · Empire arc · 20-year trend.
2. **World map** (choropleth with legend, hover tooltip, click → details).
3. **Default view (nothing selected): "The big powers."** Cards for the top ~12 by power score. Each card
   shows the score and rank, the trend arrow, three cycle chips (debt stage, internal stage, war level), and
   four headline stats: GDP-PPP share, gov debt % GDP, top-10% income share, military-spend share. Clicking
   a card opens the same detail view as clicking the map.
4. **Country detail** (side panel; deep-linkable `#USA`):
   - Summary paragraph, generated from the data in Dalio's computer-written style ("X appears to be a … power in …").
   - Cycle panel: debt stage, internal stage and war ladder with the rule or curated rationale, plus the empire-arc mini chart with the country's dot.
   - The 18 determinants: horizontal bars with score, rank of N, 20-year arrow and reliability label.
   - Proof table: every underlying statistic with value, year and source link.
   - Dalio's own words (majors only): quotes with source and date.
   - Dalio 2024 score vs. our score.
5. **Ranking table** of all countries (sortable) and the Dalio-24 comparison.
6. **Methodology section:** a condensed version of this spec, fit statistics and limitations.
7. **Footer:** "Research date: 2026-11-14 · Data vintages: IMF WEO Oct 2026, World Bank WDI (pulled
   2026-11-14), WGI 2024, COFER Q2 2026, SWIFT Jun 2026, GFCI 40 Sep 2026, FAS 2026" and how to update.

---

## 6. Updating in the future
1. Edit `research/curated.json`. Set `research_date` and refresh the COFER, SWIFT, GFCI, FAS, defaults, war
   ladder and Dalio quotes, as well as any new Dalio published index.
2. Run `python3 scripts/build_data.py`. It fetches the APIs, caches raw responses in `data/raw/`, refits
   the calibration and writes `site/data/data.js`.
3. Open `site/index.html`. The footer date comes from `research_date`.
