#!/usr/bin/env python3
"""Step 2 of the pipeline: compute Dalio-style gauges, cycle positions and power scores.

Usage:  python3 scripts/build_data.py          (reads data/raw/*, research/*.json)
Output: site/data/data.js   (window.WORLD_DATA = {...})

The method is documented in SPEC.md. In short: every gauge mixes a "size" part (share of
world, compressed with exponent P) and a "quality" part (percent rank across all countries).
Power = weighted mean of gauges, linearly calibrated to Dalio's published 2024 scores.
"""
import json, os, sys, math, statistics, itertools, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "site", "data", "data.js")

spec = importlib.util.spec_from_file_location("fetch_data", os.path.join(ROOT, "scripts", "fetch_data.py"))
fd = importlib.util.module_from_spec(spec); spec.loader.exec_module(fd)

CUR = json.load(open(os.path.join(ROOT, "research", "curated.json")))
D22 = json.load(open(os.path.join(ROOT, "research", "dalio_2022_gauges.json")))["countries"]
RESEARCH_YEAR = int(CUR["research_date"][:4])
THEN_YEAR = 2006          # baseline for the "20-year" trend (Dalio shows 20-year change)
STALE_YEARS = 5
EUZ_MEMBERS = CUR["eurozone_members"]
EUZ_EXTRA_TRADE = 0.45    # share of members' exports that leave the euro area (Eurostat, approx.)

# ----------------------------------------------------------------------------- raw loading
def load(name):
    p = os.path.join(RAW, name)
    if not os.path.exists(p):
        print("  missing raw file:", name); return {}
    return json.load(open(p))["values"]

SERIES, SRC = {}, {}
for k, label in fd.WB.items():
    SERIES[k] = load(f"wb_{k}.json"); SRC[k] = ("World Bank WDI", label, f"https://data.worldbank.org/indicator/{k}")
for k, label in fd.WGI.items():
    SERIES[k] = load(f"wb_{k}.json"); SRC[k] = ("World Bank WGI", label, "https://www.worldbank.org/en/publication/worldwide-governance-indicators")
for k, label in fd.IMF.items():
    SERIES[k] = load(f"imf_{k}.json"); SRC[k] = ("IMF " + ("Global Debt Database" if k.endswith("_LS") else "WEO"), label, f"https://www.imf.org/external/datamapper/{k}")

meta_c = json.load(open(os.path.join(RAW, "wb_countries.json")))[1]
COUNTRIES = {c["id"]: c for c in meta_c if c["region"]["id"] != "NA"}
# Taiwan is not in the World Bank database; IMF covers it.
COUNTRIES.setdefault("TWN", {"id": "TWN", "name": "Taiwan", "region": {"value": "East Asia & Pacific"},
                             "incomeLevel": {"value": "High income"}, "capitalCity": "Taipei"})
NAMES_FIX = {"KOR": "South Korea", "PRK": "North Korea", "RUS": "Russia", "IRN": "Iran", "EGY": "Egypt",
             "VEN": "Venezuela", "SYR": "Syria", "YEM": "Yemen", "TUR": "Türkiye", "LAO": "Laos",
             "COD": "DR Congo", "COG": "Congo", "GMB": "Gambia", "BHS": "Bahamas", "SVK": "Slovakia",
             "KGZ": "Kyrgyzstan", "VNM": "Vietnam", "HKG": "Hong Kong", "MAC": "Macao", "CZE": "Czechia",
             "FSM": "Micronesia", "LCA": "St. Lucia", "PSE": "Palestine", "SOM": "Somalia", "BRN": "Brunei"}


def obs(ind, iso, target=None, lo=None, hi=None):
    """Latest observation (or nearest to target year within [lo, hi]). Returns (value, year) or None."""
    s = SERIES.get(ind, {}).get(iso)
    if not s:
        return None
    items = [(int(y), v) for y, v in s.items() if v is not None]
    if target is None:
        items = [(y, v) for y, v in items if y <= RESEARCH_YEAR]
        if not items: return None
        y, v = max(items)
        return (float(v), y)
    items = [(y, v) for y, v in items if lo <= y <= hi]
    if not items: return None
    y, v = min(items, key=lambda t: (abs(t[0] - target), -t[0]))
    return (float(v), y)


def imf_mean(ind, iso, y0, y1):
    s = SERIES.get(ind, {}).get(iso) or {}
    vals = [float(s[str(y)]) for y in range(y0, y1 + 1) if s.get(str(y)) is not None]
    return (sum(vals) / len(vals), f"{y0}-{y1}") if vals else None

# ----------------------------------------------------------------------------- stats per country
def stat(v, y, src_key=None, src=None, note=None):
    if src_key:
        org, label, url = SRC[src_key]
        src = {"org": org, "label": label, "url": url, "code": src_key}
    d = {"v": v, "y": y, "src": src}
    if note: d["note"] = note
    return d


def build_stats(iso, when="now"):
    """Returns dict of stat_key -> {v, y, src}. when='now' or 'then' (~2006)."""
    T = None if when == "now" else THEN_YEAR
    rng = (None, None) if when == "now" else (THEN_YEAR - 3, THEN_YEAR + 3)

    def g(ind):
        o = obs(ind, iso, T, *rng)
        return o
    st = {}
    simple = {
        "gdp_usd": "NY.GDP.MKTP.CD", "gdp_ppp": "NY.GDP.MKTP.PP.CD", "gdp_pc_ppp": "NY.GDP.PCAP.PP.CD",
        "pop": "SP.POP.TOTL", "exports": "NE.EXP.GNFS.CD", "exports_gdp": "NE.EXP.GNFS.ZS",
        "mil_usd": "MS.MIL.XPND.CD", "mil_gdp": "MS.MIL.XPND.GD.ZS", "armed_forces": "MS.MIL.TOTL.P1",
        "rd_gdp": "GB.XPD.RSDV.GD.ZS", "patents": "IP.PAT.RESD", "researchers": "SP.POP.SCIE.RD.P6",
        "hitech": "TX.VAL.TECH.MF.ZS", "tert_enr": "SE.TER.ENRR", "tert_students": "SE.TER.ENRL",
        "hci": "HD.HCI.OVRL", "test_scores": "HD.HCI.HLOS",
        "output_per_worker": "SL.GDP.PCAP.EM.KD", "gcf_gdp": "NE.GDI.TOTL.ZS", "gcf_usd": "NE.GDI.TOTL.CD",
        "savings": "NY.GNS.ICTR.ZS", "lpi": "LP.LPI.OVRL.XQ", "mcap": "CM.MKT.LCAP.CD", "traded": "CM.MKT.TRAD.CD",
        "gini": "SI.POV.GINI", "top10": "SI.DST.10TH.10", "unemp": "SL.UEM.TOTL.ZS", "lfp": "SL.TLF.CACT.ZS",
        "age65": "SP.POP.65UP.TO.ZS", "private_credit": "FS.AST.PRVT.GD.ZS", "interest_rev": "GC.XPN.INTP.RV.ZS",
        "ext_debt": "DT.DOD.DECT.GN.ZS", "cpi_wb": "FP.CPI.TOTL.ZG", "ca_wb": "BN.CAB.XOKA.GD.ZS",
        "reserves": "FI.RES.TOTL.CD", "land": "AG.LND.TOTL.K2", "rents": "NY.GDP.TOTL.RT.ZS",
        "energy_imp": "EG.IMP.CONS.ZS",
        "wgi_rl": "GOV_WGI_RL.EST", "wgi_cc": "GOV_WGI_CC.EST", "wgi_ge": "GOV_WGI_GE.EST",
        "wgi_pv": "GOV_WGI_PV.EST", "wgi_va": "GOV_WGI_VA.EST",
        "gov_debt": "GGXWDG_NGDP", "fiscal_bal": "GGXCNL_NGDP", "primary_bal": "GGXONLB_G01_GDP_PT",
        "revenue": "GGR_G01_GDP_PT", "inflation": "PCPIPCH", "ca": "BCA_NGDPD", "ppp_share": "PPPSH",
        "unemp_imf": "LUR", "private_debt": "PVD_LS", "hh_debt": "HH_LS", "nfc_debt": "NFC_LS",
    }
    for k, ind in simple.items():
        o = g(ind)
        if o: st[k] = stat(o[0], o[1], ind)
    # IMF current-year values can be estimates: prefer last *complete* year for "now"
    if when == "now":
        for k, ind in [("gov_debt", "GGXWDG_NGDP"), ("fiscal_bal", "GGXCNL_NGDP"), ("primary_bal", "GGXONLB_G01_GDP_PT"),
                       ("revenue", "GGR_G01_GDP_PT"), ("inflation", "PCPIPCH"), ("ca", "BCA_NGDPD"), ("ppp_share", "PPPSH")]:
            o = obs(ind, iso, RESEARCH_YEAR - 1, RESEARCH_YEAR - 6, RESEARCH_YEAR - 1)
            if o: st[k] = stat(o[0], o[1], ind)
        gm = imf_mean("NGDP_RPCH", iso, RESEARCH_YEAR + 1, RESEARCH_YEAR + 5)
        if gm: st["growth_fcst"] = stat(gm[0], gm[1], "NGDP_RPCH", note="IMF forecast, average real growth")
    else:
        gm = imf_mean("NGDP_RPCH", iso, THEN_YEAR, THEN_YEAR + 4)
        if gm: st["growth_fcst"] = stat(gm[0], gm[1], "NGDP_RPCH", note="realised growth (no archived forecast)")
    # fallbacks
    if "inflation" not in st and "cpi_wb" in st: st["inflation"] = st["cpi_wb"]
    if "ca" not in st and "ca_wb" in st: st["ca"] = st["ca_wb"]
    if "unemp" not in st and "unemp_imf" in st: st["unemp"] = st["unemp_imf"]
    # derived
    if "rd_gdp" in st and "gdp_usd" in st:
        st["rd_usd"] = stat(st["rd_gdp"]["v"] * st["gdp_usd"]["v"] / 100, st["rd_gdp"]["y"],
                            src={"org": "derived", "label": "R&D spending US$ = R&D % GDP × GDP", "url": SRC["GB.XPD.RSDV.GD.ZS"][2]})
    if "tert_students" not in st and "tert_enr" in st and "pop" in st:
        st["tert_students"] = stat(st["pop"]["v"] * st["tert_enr"]["v"] / 100 * 0.07, st["tert_enr"]["y"],
                                   src={"org": "derived (World Bank)", "label": "Tertiary-student proxy = population × gross tertiary enrolment × 7% (one 5-year age cohort)", "url": SRC["SE.TER.ENRR"][2]})
    if "gdp_usd" in st and "gdp_ppp" in st:
        st["price_level"] = stat(st["gdp_usd"]["v"] / st["gdp_ppp"]["v"], st["gdp_ppp"]["y"],
                                 src={"org": "derived (World Bank ICP)", "label": "Price level ratio = GDP at market prices ÷ GDP at PPP (1 = US price level)", "url": SRC["NY.GDP.MKTP.PP.CD"][2]})
    if "primary_bal" in st and "fiscal_bal" in st:
        st["interest_gdp"] = stat(round(st["primary_bal"]["v"] - st["fiscal_bal"]["v"], 2), st["fiscal_bal"]["y"],
                                  src={"org": "derived (IMF WEO)", "label": "Net interest, % GDP = primary balance − overall balance", "url": SRC["GGXCNL_NGDP"][2]})
    if "rents" in st and "gdp_usd" in st:
        st["rents_usd"] = stat(st["rents"]["v"] * st["gdp_usd"]["v"] / 100, st["rents"]["y"],
                               src={"org": "derived", "label": "Natural-resource rents US$", "url": SRC["NY.GDP.TOTL.RT.ZS"][2]})
    # curated
    nk = CUR["nuclear_warheads"]
    nv = nk["values" if when == "now" else "values_2006"].get(iso)
    if nv is not None:
        st["nukes"] = stat(nv, RESEARCH_YEAR if when == "now" else THEN_YEAR, src={"org": "FAS", "label": "Nuclear warheads (total inventory)", "url": nk["source"]["url"]})
    rc = CUR["reserve_currency"]
    for cur, c in rc["currencies"].items():
        if c["issuer"] == iso:
            key = "cofer" if when == "now" else "cofer_2005"
            if c.get(key) is not None:
                st["cofer"] = stat(c[key], "Q2 2026" if when == "now" else 2005, src={"org": "IMF COFER", "label": f"{cur} share of world FX reserves, %", "url": rc["source_cofer"]["url"]})
            if when == "now" and c.get("swift") is not None:
                st["swift"] = stat(c["swift"], "Jun 2026", src={"org": "SWIFT", "label": f"{cur} share of global payments, %", "url": rc["source_swift"]["url"]})
    fc = CUR["financial_centers"]
    b = fc["best_by_country"].get(iso)
    if b:
        st["gfci_rank"] = stat(b[1], "Sep 2026", src={"org": "Z/Yen GFCI 40", "label": f"Best-ranked financial centre ({b[0]}), rank of {fc['total_ranked']}", "url": fc["source"]["url"]}, note=b[0])
    return st


def aggregate_euz(stats_by_iso):
    """Eurozone: sums for size measures, GDP-weighted means for ratios."""
    members = [m for m in EUZ_MEMBERS if m in stats_by_iso]
    sums = ["gdp_usd", "gdp_ppp", "pop", "exports", "mil_usd", "armed_forces", "rd_usd", "patents", "tert_students",
            "gcf_usd", "mcap", "traded", "reserves", "land", "rents_usd", "nukes"]
    out = {}
    for k in sums:
        vals = [(stats_by_iso[m][k]["v"], stats_by_iso[m][k]["y"]) for m in members if k in stats_by_iso[m]]
        if vals:
            yrs = [y for _, y in vals if isinstance(y, int)]
            out[k] = stat(sum(v for v, _ in vals), max(yrs) if yrs else vals[0][1],
                          src={"org": "aggregated", "label": f"Sum over {len(vals)} euro-area members", "url": ""})
    if "exports" in out:
        out["exports"]["v"] *= EUZ_EXTRA_TRADE
        out["exports"]["src"]["label"] = f"Extra-euro-area exports ≈ {int(EUZ_EXTRA_TRADE*100)}% of members' total exports"
    for k in set().union(*[set(stats_by_iso[m]) for m in members]) - set(sums):
        vals = [(stats_by_iso[m][k]["v"], stats_by_iso[m].get("gdp_usd", {"v": 0})["v"], stats_by_iso[m][k]["y"])
                for m in members if k in stats_by_iso[m] and isinstance(stats_by_iso[m][k]["v"], (int, float))]
        if k in ("gfci_rank",):
            vals = [(stats_by_iso[m][k]["v"], 1, stats_by_iso[m][k]["y"]) for m in members if k in stats_by_iso[m]]
            best = min(vals)[0]
            m_best = [m for m in members if k in stats_by_iso[m] and stats_by_iso[m][k]["v"] == best][0]
            out[k] = dict(stats_by_iso[m_best][k]); continue
        wsum = sum(w for _, w, _ in vals)
        if vals and wsum > 0:
            yrs = [y for _, _, y in vals if isinstance(y, int)]
            out[k] = stat(sum(v * w for v, w, _ in vals) / wsum, max(yrs) if yrs else vals[0][2],
                          src={"org": "aggregated", "label": f"GDP-weighted mean over {len(vals)} members", "url": ""})
    if "gdp_ppp" in out and "pop" in out:
        out["gdp_pc_ppp"] = stat(out["gdp_ppp"]["v"] / out["pop"]["v"], out["gdp_ppp"]["y"], src={"org": "aggregated", "label": "GDP PPP / population", "url": ""})
    return out

# ----------------------------------------------------------------------------- gauges
# size: list of (stat, weight);  quality: list of (stat, weight, higher_is_better)
GAUGES = [
    # --- big cycles
    dict(id="debt", name="Debt Burden", group="cycle", rel="Reliable", size_w=0,
         quality=[("gov_debt", 2, False), ("interest_gdp", 1.5, False), ("interest_rev", 1, False), ("fiscal_bal", 1, True),
                  ("private_debt", 1, False), ("ca", 1, True), ("ext_debt", 1, False), ("inflation", 1, False)],
         desc="Debt levels, debt service, deficits, external balances and inflation. Low = heavy debt burden (Dalio excludes reserve-currency status)."),
    dict(id="growth", name="Expected Growth", group="cycle", rel="Reliable", size_w=0,
         quality=[("growth_fcst", 1, True)], desc="IMF real GDP growth forecast, average of the next 5 years."),
    dict(id="gaps", name="Gaps in Wealth, Opportunity & Values", group="cycle", rel="So-so", size_w=0,
         quality=[("gini", 1, False), ("top10", 1, False)], desc="Income inequality (Gini, top-10% income share). Low = large gaps."),
    dict(id="conflict", name="Internal Conflict", group="cycle", rel="So-so", size_w=0,
         quality=[("wgi_pv", 2, True), ("wgi_va", 1, True)], desc="Political stability/absence of violence and voice & accountability. Low = high internal conflict."),
    dict(id="external", name="External Order", group="cycle", rel="So-so", size_w=0, quality=[],
         desc="Position on Dalio's war ladder (trade → technology → geopolitical → capital → military). Low = deeper in conflict."),
    # --- key eight
    dict(id="education", name="Education", group="key", rel="Reliable", size_w=0.5, size=[("tert_students", 1)],
         quality=[("tert_enr", 1, True), ("test_scores", 1, True), ("hci", 1, True)],
         desc="Half the number of tertiary students (share of world), half quality (enrolment, test scores, human capital)."),
    dict(id="innovation", name="Innovation & Technology", group="key", rel="Reliable", size_w=0.5, size=[("rd_usd", 1), ("patents", 1)],
         quality=[("rd_gdp", 1, True), ("researchers", 1, True), ("hitech", 0.5, True)],
         desc="Half absolute share of R&D spending and patents, half intensity (R&D % GDP, researchers per million, high-tech exports)."),
    dict(id="cost", name="Cost Competitiveness", group="key", rel="Reliable", size_w=0,
         quality=[("price_level", 2, False), ("hci", 1, True)],
         desc="What one gets for what one pays: low price level (cheap labour and inputs) adjusted for human-capital quality."),
    dict(id="military", name="Military Strength", group="key", rel="Reliable", size_w=0.85, size=[("mil_usd", 3), ("armed_forces", 1), ("nukes", 1)],
         quality=[("mil_gdp", 1, True)], desc="Mostly absolute share of world military spending, plus personnel and nuclear warheads."),
    dict(id="trade", name="Trade", group="key", rel="Reliable", size_w=1, size=[("exports", 1)], quality=[],
         desc="Exports of goods and services as a share of the world."),
    dict(id="output", name="Economic Output", group="key", rel="Reliable", size_w=0.75, size=[("gdp_ppp", 1)],
         quality=[("gdp_pc_ppp", 1, True)], desc="Share of world GDP (PPP), with some weight on GDP per capita."),
    dict(id="markets", name="Markets & Financial Center", group="key", rel="Reliable", size_w=0.6, size=[("mcap", 1), ("traded", 1)],
         quality=[("gfci", 1, True)], desc="Share of world stock-market capitalisation and trading, plus the GFCI rank of the best financial centre."),
    dict(id="reserve", name="Reserve Currency Status", group="key", rel="Reliable", size_w=1, size=[("cofer", 2), ("swift", 1)], quality=[],
         desc="Share of world central-bank reserves (IMF COFER) and of global payments (SWIFT) in the country's currency."),
    # --- additional
    dict(id="infra", name="Infrastructure & Investment", group="add", rel="Reliable", size_w=0.5, size=[("gcf_usd", 1)],
         quality=[("gcf_gdp", 1, True), ("savings", 1, True), ("lpi", 1, True)], desc="Share of world investment, investment and savings rates, logistics quality."),
    dict(id="governance", name="Governance / Rule of Law", group="add", rel="Reliable", size_w=0,
         quality=[("wgi_rl", 1, True), ("wgi_cc", 1, True), ("wgi_ge", 1, True)], desc="WGI rule of law, control of corruption, government effectiveness."),
    dict(id="geology", name="Geology", group="add", rel="Reliable", size_w=0.6, size=[("land", 1), ("rents_usd", 1)],
         quality=[("energy_imp", 1, False), ("rents", 0.5, True)], desc="Land area, natural-resource production (rents) and energy self-sufficiency."),
    dict(id="alloc", name="Resource-Allocation Efficiency", group="add", rel="So-so", size_w=0,
         quality=[("unemp", 1, False), ("output_per_worker", 1, True)], desc="Does the country employ its people and capital well? (unemployment, output per worker)."),
    dict(id="character", name="Character / Civility / Determination", group="add", rel="So-so", size_w=0,
         quality=[("lfp", 1, True), ("savings", 1, True)], desc="Proxy for work ethic and self-reliance: labour-force participation and savings."),
    dict(id="nature", name="Acts of Nature", group="add", rel="So-so", size_w=0, quality=[],
         desc="Not measured: there is no open, comparable global series. Dalio himself rates this gauge 'so-so'."),
]
GMAP = {g["id"]: g for g in GAUGES}
KEY8 = [g["id"] for g in GAUGES if g["group"] == "key"]


def percentile_fn(values):
    vs = sorted(values)
    n = len(vs)
    def f(x):
        if n <= 1: return 0.5
        import bisect
        lo = bisect.bisect_left(vs, x); hi = bisect.bisect_right(vs, x)
        return ((lo + hi) / 2) / n
    return f


def compute_gauges(stats, real_isos, P, ladder):
    """stats: iso -> stats. Returns iso -> gauge_id -> {score, size, quality}"""
    # world totals for size stats (individual countries only)
    for iso, st in stats.items():
        if "gfci_rank" in st:
            st["gfci"] = {"v": 1 - (st["gfci_rank"]["v"] - 1) / CUR["financial_centers"]["total_ranked"], "y": st["gfci_rank"]["y"]}
    size_keys = {k for g in GAUGES for k, _ in g.get("size", [])}
    qual_keys = {k for g in GAUGES for k, _, _ in g.get("quality", [])}
    world, maxshare = {}, {}
    for k in size_keys:
        vals = {i: stats[i][k]["v"] for i in real_isos if k in stats[i] and stats[i][k]["v"] is not None}
        if k == "cofer":
            world[k] = 100.0
        elif k == "swift":
            world[k] = 100.0
        else:
            world[k] = sum(vals.values()) or 1
        maxshare[k] = max(vals.values()) / world[k] if vals else 1
    pct = {}
    for k in qual_keys:
        vals = [stats[i][k]["v"] for i in real_isos if k in stats[i]]
        pct[k] = percentile_fn(vals)
    out = {}
    for iso, st in stats.items():
        res = {}
        for g in GAUGES:
            gid = g["id"]
            if gid == "external":
                lvl = ladder.get(iso, 0)
                res[gid] = {"score": round(1 - lvl / 5, 4), "size": None, "quality": None}
                continue
            # size
            sz, szw = 0, 0
            for k, w in g.get("size", []):
                if k == "cofer" or k == "swift":
                    v = st.get(k, {"v": 0})["v"]   # non-issuers have ~0 share (Dalio scores them at the floor)
                    if iso in EUZ_MEMBERS: continue
                elif k in st:
                    v = st[k]["v"]
                else:
                    continue
                share = max(v, 0) / world[k]
                sz += w * min(1, (share / maxshare[k]) ** P); szw += w
            size = sz / szw if szw else None
            q, qw = 0, 0
            for k, w, hib in g.get("quality", []):
                if k == "gfci":
                    v = st.get("gfci", {"v": None})["v"]
                    q += w * (v if v is not None else 0); qw += w; continue
                if k not in st: continue
                p = pct[k](st[k]["v"])
                q += w * (p if hib else 1 - p); qw += w
            quality = q / qw if qw else None
            if size is None and quality is None:
                res[gid] = None; continue
            sw = g["size_w"]
            if size is None: score = quality
            elif quality is None: score = size
            else: score = sw * size + (1 - sw) * quality
            res[gid] = {"score": round(score, 4), "size": None if size is None else round(size, 4),
                        "quality": None if quality is None else round(quality, 4)}
        # civil-war states: internal conflict floor
        if iso in CUR["internal_stage_lists"]["stage6"] and res.get("conflict"):
            res["conflict"]["score"] = min(res["conflict"]["score"], 0.05)
        out[iso] = res
    return out


def raw_power(gs, wa, wc, gauge_subset=None):
    tot, wt = 0, 0
    for g in GAUGES:
        gid = g["id"]
        if gauge_subset and gid not in gauge_subset: continue
        v = gs.get(gid)
        if not v: continue
        w = 1 if g["group"] == "key" else wa if g["group"] == "add" else wc
        if gid in ("external",): w = wc
        tot += w * v["score"]; wt += w
    return tot / wt if wt else None


def linfit(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return num / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))


def spearman(xs, ys):
    def ranks(a):
        o = sorted(range(len(a)), key=lambda i: a[i]); r = [0] * len(a)
        for k, i in enumerate(o): r[i] = k
        return r
    return pearson(ranks(xs), ranks(ys))

# ----------------------------------------------------------------------------- cycles
DEBT_LABELS = {1: "Sound money / low debt", 2: "Debt build-up", 3: "Top / late-cycle squeeze",
               4: "Deleveraging / debt crisis", 5: "Crisis receding / new equilibrium"}
INT_LABELS = {1: "New order consolidating", 2: "Systems & bureaucracies being built", 3: "Peace & prosperity",
              4: "Excesses & widening gaps", 5: "Bad finances & intense conflict", 6: "Civil war / revolution"}
WAR_LABELS = CUR["war_ladder"]["_levels"]


def debt_stage(iso, st, gs):
    m = CUR["majors"].get(iso)
    if m and m.get("debt"):
        return {"stage": m["debt"][0], "why": m["debt"][1], "basis": "curated"}
    l4, l5 = CUR["debt_stage_lists"]["stage4"], CUR["debt_stage_lists"]["stage5"]
    if iso in l4: return {"stage": 4, "why": l4[iso], "basis": "curated list"}
    if iso in l5: return {"stage": 5, "why": l5[iso], "basis": "curated list"}
    risk = 1 - gs["debt"]["score"] if gs.get("debt") else None
    gd = st.get("gov_debt", {}).get("v"); ir = st.get("interest_rev", {}).get("v"); inf = st.get("inflation", {}).get("v")
    if (inf is not None and inf >= 40) or (ir is not None and ir >= 35):
        return {"stage": 4, "why": f"Rule: inflation ≥ 40% or interest ≥ 35% of revenue (inflation {fmt(inf)}%, interest/revenue {fmt(ir)}%).", "basis": "computed", "risk": risk}
    if risk is None:
        return {"stage": None, "why": "Insufficient debt data.", "basis": "computed"}
    if risk >= 0.6 or (gd is not None and gd >= 100) or (ir is not None and ir >= 15):
        why = f"Rule: debt-risk ≥ 0.60, or gov debt ≥ 100% GDP, or interest ≥ 15% of revenue (debt-risk {risk:.2f}, gov debt {fmt(gd)}%, interest/revenue {fmt(ir)}%)."
        return {"stage": 3, "why": why, "basis": "computed", "risk": risk}
    if risk >= 0.35:
        return {"stage": 2, "why": f"Rule: debt-risk between 0.35 and 0.60 (debt-risk {risk:.2f}, gov debt {fmt(gd)}% GDP).", "basis": "computed", "risk": risk}
    return {"stage": 1, "why": f"Rule: debt-risk < 0.35 (debt-risk {risk:.2f}, gov debt {fmt(gd)}% GDP).", "basis": "computed", "risk": risk}


def internal_stage(iso, st, gs, dstage):
    m = CUR["majors"].get(iso)
    lists = CUR["internal_stage_lists"]
    if iso in lists["stage6"]: return {"stage": 6, "why": lists["stage6"][iso], "basis": "curated list"}
    if m and m.get("internal"):
        return {"stage": m["internal"][0], "why": m["internal"][1], "basis": "curated"}
    if iso in lists["stage1"]: return {"stage": 1, "why": lists["stage1"][iso], "basis": "curated list"}
    pv = st.get("wgi_pv", {}).get("v")
    if pv is not None and pv <= -2.0:
        return {"stage": 6, "why": f"Rule: WGI political stability ≤ −2.0 ({pv:.2f}).", "basis": "computed"}
    gaps = gs.get("gaps", {}) and gs["gaps"] and gs["gaps"]["score"]
    conf = gs.get("conflict") and gs["conflict"]["score"]
    risk = (1 - gs["debt"]["score"]) if gs.get("debt") else 0.5
    if gaps is None and conf is None:
        return {"stage": None, "why": "Insufficient data.", "basis": "computed"}
    gaps = 0.5 if gaps is None else gaps; conf = 0.5 if conf is None else conf
    stress = 0.4 * (1 - gaps) + 0.4 * (1 - conf) + 0.2 * risk
    ds = dstage.get("stage") or 0
    detail = f"internal-stress {stress:.2f} = 0.4·gaps {1-gaps:.2f} + 0.4·conflict {1-conf:.2f} + 0.2·debt-risk {risk:.2f}"
    if stress >= 0.6 and (ds >= 3 or (pv is not None and pv < -1)):
        return {"stage": 5, "why": f"Rule: stress ≥ 0.60 and (debt stage ≥ 3 or political stability < −1); {detail}.", "basis": "computed", "stress": stress}
    if stress >= 0.45:
        return {"stage": 4, "why": f"Rule: stress ≥ 0.45; {detail}.", "basis": "computed", "stress": stress}
    return {"stage": 3, "why": f"Rule: stress < 0.45; {detail}.", "basis": "computed", "stress": stress}


def fmt(v, d=0):
    return "n/a" if v is None else f"{v:,.{d}f}"


def trajectory(delta):
    if delta is None: return "unknown trajectory"
    for th, lab in [(0.05, "rapid ascent"), (0.025, "ascent"), (0.008, "gradual ascent"), (-0.008, "a flat trajectory"),
                    (-0.025, "gradual decline"), (-0.05, "decline")]:
        if delta >= th: return lab
    return "rapid decline"


def tier(score):
    if score is None: return "unscored"
    if score >= 0.5: return "a strong power"
    if score >= 0.27: return "a middle-of-the-pack power"
    if score >= 0.18: return "a modest power"
    return "not a meaningful global power"

# ----------------------------------------------------------------------------- main
def main():
    real = [i for i in COUNTRIES]
    st_now = {i: build_stats(i, "now") for i in real}
    st_then = {i: build_stats(i, "then") for i in real}
    st_now["EUZ"] = aggregate_euz(st_now); st_then["EUZ"] = aggregate_euz(st_then)
    ladder = {k: v[0] for k, v in CUR["war_ladder"]["countries"].items() if not k.startswith("_")}

    d24 = CUR["dalio_published_scores"]["2024"]
    best = None
    for P in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 1.0]:
        gs = compute_gauges(st_now, real, P, ladder)
        for wa in [0, 0.25, 0.5, 0.75, 1]:
            for wc in [0, 0.25, 0.5]:
                xs, ys = [], []
                for iso, dv in d24.items():
                    rp = raw_power(gs[iso], wa, wc)
                    if rp is not None: xs.append(rp); ys.append(dv)
                a, b = linfit(xs, ys)
                err = sum((a + b * x - y) ** 2 for x, y in zip(xs, ys))
                if best is None or err < best[0]:
                    best = (err, P, wa, wc, a, b)
    _, P, WA, WC, A, B = best
    print(f"calibration: P={P} wa={WA} wc={WC} a={A:.3f} b={B:.3f}")
    G = compute_gauges(st_now, real, P, ladder)
    GT = compute_gauges(st_then, real, P, {})   # no historical war ladder
    # like-for-like "now" for the trend: only statistics that also exist ~THEN_YEAR for that country
    st_match = {i: {k: v for k, v in st_now[i].items() if k in st_then[i] or k in ("gfci_rank",)} for i in st_now}
    GM = compute_gauges(st_match, real, P, ladder)

    def cal(x): return None if x is None else max(0.0, min(1.0, A + B * x))
    # gauges with usable history for trend (exclude curated-only/forecast gauges)
    trend_set = [g["id"] for g in GAUGES if g["id"] not in ("external", "growth", "nature")]

    entities = {}
    isos = real + ["EUZ"]
    for iso in isos:
        gs, gt, gm = G[iso], GT[iso], GM[iso]
        p_now = cal(raw_power(gs, WA, WC))
        both = [k for k in trend_set if gm.get(k) and gt.get(k)]
        pn_sub, pt_sub = raw_power(gm, WA, WC, both), raw_power(gt, WA, WC, both)
        delta = None
        if pn_sub is not None and pt_sub is not None:
            # count only if 'then' has reasonable coverage of key gauges
            cov = sum(1 for k in KEY8 if k in both) / len(KEY8)
            if cov >= 0.6: delta = round(B * (pn_sub - pt_sub), 4)
        entities[iso] = {"power": p_now, "delta": delta}

    # ranks
    scored = sorted([i for i in real if entities[i]["power"] is not None], key=lambda i: -entities[i]["power"])
    d24_set = list(d24.keys())
    scored24 = sorted([i for i in d24_set if entities[i]["power"] is not None], key=lambda i: -entities[i]["power"])
    gauge_rank = {}
    for g in GAUGES:
        vals = sorted([(G[i][g["id"]]["score"], i) for i in real if G[i].get(g["id"])], reverse=True)
        gauge_rank[g["id"]] = {i: (k + 1, len(vals)) for k, (_, i) in enumerate(vals)}
        # EUZ rank: position among countries
        if G["EUZ"].get(g["id"]):
            s = G["EUZ"][g["id"]]["score"]
            gauge_rank[g["id"]]["EUZ"] = (1 + sum(1 for v, _ in vals if v > s), len(vals))

    out = {}
    for iso in isos:
        st, gs, gt = st_now[iso], G[iso], GT[iso]
        c = COUNTRIES.get(iso, {"name": "Eurozone", "region": {"value": "Europe & Central Asia"}, "incomeLevel": {"value": "High income"}})
        name = NAMES_FIX.get(iso, c["name"])
        pw = entities[iso]["power"]; dl = entities[iso]["delta"]
        ds = debt_stage(iso, st, gs)
        ins = internal_stage(iso, st, gs, ds)
        wl = CUR["war_ladder"]["countries"].get(iso)
        ext = {"level": wl[0] if wl else 0, "why": wl[1] if wl else "No major external conflict identified as of the research date.",
               "basis": "curated" if wl else "default"}
        # empire arc position
        def gsc(k, src=gs): return src[k]["score"] if src.get(k) else None
        lead = [x for x in (gsc("education"), gsc("innovation"), gsc("cost")) if x is not None]
        lag = [x for x in (gsc("markets"), gsc("reserve")) if x is not None]
        lag_minus_lead = (statistics.mean(lag) - statistics.mean(lead)) if lead and lag else 0
        u = 0 if dl is None else -max(-1, min(1, dl / 0.05)) * 0.75
        u += max(-0.25, min(0.25, lag_minus_lead * 0.5))
        u = max(-0.95, min(0.95, u))
        phase = "Rising" if u < -0.2 else "Declining" if u > 0.2 else "Near peak / plateau"
        if pw is not None and pw < 0.18 and phase == "Near peak / plateau":
            phase = "Flat"
        gauges_out = {}
        for g in GAUGES:
            v = gs.get(g["id"]); t = gt.get(g["id"]); vm = GM[iso].get(g["id"])
            if not v: gauges_out[g["id"]] = None; continue
            r = gauge_rank[g["id"]].get(iso)
            gauges_out[g["id"]] = {"s": v["score"], "sz": v["size"], "q": v["quality"],
                                   "t": None if not t or not vm or g["id"] in ("external", "growth") else round(vm["score"] - t["score"], 3),
                                   "r": r[0] if r else None, "n": r[1] if r else None}
        rank = scored.index(iso) + 1 if iso in scored else None
        stats_out = {k: v for k, v in st.items() if k not in ("gfci",)}
        for k, v in stats_out.items():
            if isinstance(v.get("v"), float): v["v"] = round(v["v"], 4 if abs(v["v"]) < 10 else 2)
            if isinstance(v.get("y"), int) and RESEARCH_YEAR - v["y"] > STALE_YEARS: v["stale"] = True
        # shares of world (for display)
        shares = {}
        for k in ("gdp_ppp", "exports", "mil_usd", "rd_usd", "mcap", "pop", "gdp_usd", "patents"):
            tot = sum(st_now[i][k]["v"] for i in real if k in st_now[i])
            if k in st and tot: shares[k] = round(100 * st[k]["v"] / tot, 2)
        m = CUR["majors"].get(iso, {})
        e = {
            "iso": iso, "name": name, "region": c["region"]["value"], "income": c.get("incomeLevel", {}).get("value"),
            "power": None if pw is None else round(pw, 3), "delta20": dl, "rank": rank, "nRanked": len(scored),
            "rank24": scored24.index(iso) + 1 if iso in scored24 else None,
            "dalio2024": d24.get(iso), "dalio2022": CUR["dalio_published_scores"]["2022"].get(iso),
            "verdict2022": CUR["dalio_2022_verdicts"].get(iso), "dalio2022gauges": D22.get(iso),
            "tier": tier(pw), "trajectory": trajectory(dl),
            "cycles": {"debt": ds, "internal": ins, "external": ext,
                       "arc": {"u": round(u, 3), "phase": phase, "lagMinusLead": round(lag_minus_lead, 3)}},
            "gauges": gauges_out, "stats": stats_out, "shares": shares, "quotes": m.get("quotes", []),
            "isMajor": iso in d24 or iso in CUR["majors"], "inDalio24": iso in d24,
        }
        for k in ("debt", "internal"):
            s = e["cycles"][k]
            for kk in ("risk", "stress"):
                if kk in s and s[kk] is not None: s[kk] = round(s[kk], 3)
        e["summary"] = summarize(e)
        out[iso] = e

    # fit stats
    xs = [out[i]["power"] for i in d24 if out[i]["power"] is not None]
    ys = [d24[i] for i in d24 if out[i]["power"] is not None]
    fit = {"P": P, "wa": WA, "wc": WC, "a": round(A, 4), "b": round(B, 4), "n": len(xs),
           "pearson": round(pearson(xs, ys), 3), "spearman": round(spearman(xs, ys), 3),
           "mae": round(statistics.mean(abs(x - y) for x, y in zip(xs, ys)), 3)}
    print("fit:", fit)

    # map: ISO numeric -> alpha3
    codes = json.load(open(os.path.join(RAW, "iso-codes.json")))
    num2a3 = {}
    for row in codes:
        if isinstance(row, list) and len(row) >= 3: num2a3[str(row[2]).zfill(3)] = row[1]
    num2a3.update({"-99": None})
    fetched = json.load(open(os.path.join(RAW, "_fetched.json")))["fetched_at"]
    data = {
        "meta": {"research_date": CUR["research_date"], "data_fetched": fetched, "edition_note": CUR["edition_note"],
                 "then_year": THEN_YEAR, "fit": fit, "sources": CUR["sources"],
                 "dalio_sources": CUR["dalio_published_scores"], "war_levels": WAR_LABELS,
                 "debt_labels": DEBT_LABELS, "internal_labels": INT_LABELS,
                 "eurozone_members": EUZ_MEMBERS,
                 "vintages": vintages()},
        "gauges": [dict({k: g[k] for k in ("id", "name", "group", "rel", "desc", "size_w")},
                         size=[k for k, _ in g.get("size", [])],
                         quality=[("gfci_rank" if k == "gfci" else k) for k, _, _ in g.get("quality", [])]) for g in GAUGES],
        "entities": out, "num2iso": num2a3,
    }
    with open(OUT, "w") as f:
        f.write("/* generated by scripts/build_data.py — do not edit */\nwindow.WORLD_DATA = ")
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        f.write(";\n")
    # map geometry as a script so the site works from file:// (no fetch needed)
    topo = os.path.join(ROOT, "site", "data", "countries-110m.json")
    with open(os.path.join(ROOT, "site", "data", "countries-110m.js"), "w") as f:
        f.write("window.WORLD_TOPO = " + open(topo).read().strip() + ";\n")
    print("wrote", os.path.relpath(OUT, ROOT), f"{os.path.getsize(OUT)/1e6:.2f} MB,", len(out), "entities")
    for iso in scored24:
        e = out[iso]
        print(f"  {iso} ours={e['power']:.2f} dalio24={e['dalio2024']} Δ20={e['delta20']} debt={e['cycles']['debt']['stage']} int={e['cycles']['internal']['stage']} war={e['cycles']['external']['level']} arc={e['cycles']['arc']['phase']}")


def vintages():
    v = {}
    for k in ("NY.GDP.MKTP.PP.CD", "MS.MIL.XPND.CD", "GOV_WGI_RL.EST", "SI.POV.GINI"):
        p = os.path.join(RAW, f"wb_{k}.json")
        if os.path.exists(p): v[k] = json.load(open(p)).get("lastupdated")
    return v


def summarize(e):
    """Dalio-style computer-generated summary paragraph."""
    n = e["name"]; g = e["gauges"]; s = e["stats"]
    if e["power"] is None:
        return f"There is not enough data to score {n}'s overall power."
    the = "the " if e["iso"] in ("USA", "GBR", "NLD", "ARE", "PHL", "CZE", "DOM", "CAF", "COD", "COG", "GMB", "BHS") else ""
    parts = [f"Based on the latest readings, {the}{n} appears to be {e['tier']} (#{e['rank']} of {e['nRanked']} countries"
             + (f", #{e['rank24']} among Dalio's 24" if e.get("rank24") else "") + f") on {e['trajectory']}."]
    key = [(gid, g[gid]["s"]) for gid in KEY8 + ["infra", "governance", "geology"] if g.get(gid)]
    key.sort(key=lambda t: -t[1])
    strong = [GMAP[k]["name"].lower() for k, v in key[:3] if v >= 0.6]
    weak = [GMAP[k]["name"].lower() for k, v in key[-3:] if v < 0.4]
    if strong: parts.append("Its main strengths are " + join(strong) + ".")
    if weak: parts.append("Its weaknesses are " + join(weak) + ".")
    d = e["cycles"]["debt"]; i = e["cycles"]["internal"]; x = e["cycles"]["external"]
    if d.get("stage"):
        bits = []
        if "gov_debt" in s: bits.append(f"government debt is {s['gov_debt']['v']:.0f}% of GDP")
        if "fiscal_bal" in s: bits.append(f"the budget balance is {s['fiscal_bal']['v']:+.1f}% of GDP")
        if "interest_gdp" in s and s["interest_gdp"]["v"] > 0: bits.append(f"net interest costs {s['interest_gdp']['v']:.1f}% of GDP")
        parts.append(f"In the big debt cycle it is at stage {d['stage']} ({DEBT_LABELS[d['stage']].lower()})"
                     + (": " + join(bits) if bits else "") + ".")
    if "growth_fcst" in s:
        parts.append(f"Expected real growth over the next five years is {s['growth_fcst']['v']:.1f}% a year (IMF).")
    if i.get("stage"):
        gi = []
        if "top10" in s: gi.append(f"the top 10% take {s['top10']['v']:.0f}% of income")
        if "gini" in s: gi.append(f"the Gini index is {s['gini']['v']:.0f}")
        parts.append(f"Internally it is at stage {i['stage']} of 6 ({INT_LABELS[i['stage']].lower()})" + ("; " + join(gi) if gi else "") + ".")
    parts.append(f"Externally: {WAR_LABELS[x['level']].lower()}." if x["level"] else "It is not in a major external conflict.")
    return " ".join(parts)


def join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


if __name__ == "__main__":
    main()
