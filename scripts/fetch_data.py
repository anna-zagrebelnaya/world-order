#!/usr/bin/env python3
"""Step 1 of the pipeline: download raw public data into data/raw/.

Usage:  python3 scripts/fetch_data.py [--force]

Sources (all free, no key):
  * World Bank WDI / WGI API   https://api.worldbank.org/v2/
  * IMF DataMapper API (WEO + Global Debt Database)  https://www.imf.org/external/datamapper/api/v1/
  * world-atlas TopoJSON + ISO-3166 numeric codes (map geometry), d3 + topojson-client (vendored)
"""
import json, os, sys, time, subprocess, urllib.request, concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
SITE = os.path.join(ROOT, "site")
FORCE = "--force" in sys.argv

# World Bank indicators (source 2 = WDI unless noted)
WB = {
    # size / output
    "NY.GDP.MKTP.CD": "GDP, current US$",
    "NY.GDP.MKTP.PP.CD": "GDP, PPP (current intl $)",
    "NY.GDP.PCAP.PP.CD": "GDP per capita, PPP",
    "SP.POP.TOTL": "Population",
    # trade
    "NE.EXP.GNFS.CD": "Exports of goods & services, US$",
    "NE.EXP.GNFS.ZS": "Exports, % of GDP",
    # military
    "MS.MIL.XPND.CD": "Military expenditure, US$ (SIPRI)",
    "MS.MIL.XPND.GD.ZS": "Military expenditure, % GDP (SIPRI)",
    "MS.MIL.TOTL.P1": "Armed forces personnel",
    # innovation
    "GB.XPD.RSDV.GD.ZS": "R&D expenditure, % GDP",
    "IP.PAT.RESD": "Patent applications, residents",
    "SP.POP.SCIE.RD.P6": "Researchers in R&D per million",
    "TX.VAL.TECH.MF.ZS": "High-tech exports, % manufactured exports",
    # education
    "SE.TER.ENRR": "Tertiary enrolment, gross %",
    "SE.TER.ENRL": "Tertiary students, total",
    "HD.HCI.OVRL": "Human Capital Index (0-1)",
    "HD.HCI.HLOS": "Harmonized test scores",
    # competitiveness
    "SL.GDP.PCAP.EM.KD": "GDP per person employed (2021 PPP $)",
    # infrastructure & investment
    "NE.GDI.TOTL.ZS": "Gross capital formation, % GDP",
    "NE.GDI.TOTL.CD": "Gross capital formation, US$",
    "NY.GNS.ICTR.ZS": "Gross savings, % GDP",
    "LP.LPI.OVRL.XQ": "Logistics Performance Index (1-5)",
    # markets
    "CM.MKT.LCAP.CD": "Stock market capitalisation, US$",
    "CM.MKT.TRAD.CD": "Stocks traded, value US$",
    # gaps
    "SI.POV.GINI": "Gini index",
    "SI.DST.10TH.10": "Income share of top 10%",
    # efficiency / character
    "SL.UEM.TOTL.ZS": "Unemployment, % labour force (ILO)",
    "SL.TLF.CACT.ZS": "Labour-force participation, %",
    "SP.POP.65UP.TO.ZS": "Population 65+, %",
    "FS.AST.PRVT.GD.ZS": "Domestic credit to private sector, % GDP",
    # debt
    "GC.XPN.INTP.RV.ZS": "Interest payments, % of revenue",
    "DT.DOD.DECT.GN.ZS": "External debt stocks, % GNI",
    "FP.CPI.TOTL.ZG": "Inflation, CPI %",
    "BN.CAB.XOKA.GD.ZS": "Current account balance, % GDP",
    "FI.RES.TOTL.CD": "Total reserves incl. gold, US$",
    # geology
    "AG.LND.TOTL.K2": "Land area, km2",
    "NY.GDP.TOTL.RT.ZS": "Natural-resource rents, % GDP",
    "EG.IMP.CONS.ZS": "Net energy imports, % energy use",
}
WGI = {  # source 3 = Worldwide Governance Indicators
    "GOV_WGI_RL.EST": "Rule of Law (WGI, -2.5..2.5)",
    "GOV_WGI_CC.EST": "Control of Corruption (WGI)",
    "GOV_WGI_GE.EST": "Government Effectiveness (WGI)",
    "GOV_WGI_PV.EST": "Political Stability & Absence of Violence (WGI)",
    "GOV_WGI_VA.EST": "Voice & Accountability (WGI)",
}
IMF = {
    "GGXWDG_NGDP": "General government gross debt, % GDP",
    "GGXCNL_NGDP": "General government net lending/borrowing, % GDP",
    "GGXONLB_G01_GDP_PT": "General government primary balance, % GDP (Fiscal Monitor)",
    "GGR_G01_GDP_PT": "General government revenue, % GDP (Fiscal Monitor)",
    "NGDP_RPCH": "Real GDP growth, % (incl. forecasts)",
    "PCPIPCH": "Inflation, average CPI %",
    "BCA_NGDPD": "Current account, % GDP",
    "PPPSH": "Share of world GDP (PPP), %",
    "LUR": "Unemployment rate, %",
    "PVD_LS": "Private debt, loans & debt securities, % GDP",
    "HH_LS": "Household debt, % GDP",
    "NFC_LS": "Non-financial corporate debt, % GDP",
}


def http_json(url, tries=6, ua=None):
    """Uses curl: it is far faster/more reliable than urllib against the World Bank API here.
    The IMF API rejects browser-like User-Agents, so curl's default UA is kept."""
    last = None
    for i in range(tries):
        try:
            cmd = ["curl", "-s", "-f", "-m", "180", "-H", "Accept: application/json"]
            if ua: cmd += ["-A", ua]
            r = subprocess.run(cmd + [url], capture_output=True, check=True)
            d = json.loads(r.stdout)
            if isinstance(d, list) and len(d) < 2:
                raise RuntimeError(f"API error: {d}")
            return d
        except Exception as e:  # noqa
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"{url}: {last}")


def http_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "world-order-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def cached(name, fn):
    path = os.path.join(RAW, name)
    if os.path.exists(path) and not FORCE:
        return
    data = fn()
    with open(path, "w") as f:
        json.dump(data, f)
    print("  saved", name)


WB_SOURCE = {"HD.HCI.OVRL": 63, "HD.HCI.HLOS": 63}   # Human Capital Index database


def wb_fetch(ind, source=None):
    source = source or WB_SOURCE.get(ind, 2)
    # non-WDI sources reject the date filter; fetch everything
    date = "&date=2000:2026" if source == 2 else ""
    url = (f"https://api.worldbank.org/v2/country/all/indicator/{ind}"
           f"?format=json&per_page=20000{date}&source={source}")
    d = http_json(url)
    meta, rows = d[0], d[1] or []
    if meta.get("pages", 1) > 1:
        for p in range(2, meta["pages"] + 1):
            rows += http_json(url + f"&page={p}")[1] or []
    out = {}
    for r in rows:
        if r["value"] is None or not r["countryiso3code"] or not r["date"][:4].isdigit():
            continue
        out.setdefault(r["countryiso3code"], {})[r["date"][:4]] = r["value"]
    return {"indicator": ind, "lastupdated": meta.get("lastupdated"), "values": out}


def imf_fetch(ind):
    d = http_json(f"https://www.imf.org/external/datamapper/api/v1/{ind}")  # curl default UA (IMF blocks browser-like UAs)
    return {"indicator": ind, "values": d.get("values", {}).get(ind, {})}


def main():
    os.makedirs(RAW, exist_ok=True)
    jobs = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for ind in WB:
            jobs.append(ex.submit(cached, f"wb_{ind}.json", lambda i=ind: wb_fetch(i)))
        for ind in WGI:
            jobs.append(ex.submit(cached, f"wb_{ind}.json", lambda i=ind: wb_fetch(i, 3)))
        for ind in IMF:
            jobs.append(ex.submit(cached, f"imf_{ind}.json", lambda i=ind: imf_fetch(i)))
        jobs.append(ex.submit(cached, "wb_countries.json", lambda: http_json(
            "https://api.worldbank.org/v2/country?format=json&per_page=400")))
        for j in jobs:
            try:
                j.result()
            except Exception as e:
                print("  FAILED:", e)

    # Map geometry + ISO numeric codes + vendored JS libraries
    vend = os.path.join(SITE, "vendor")
    os.makedirs(vend, exist_ok=True)
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    assets = {
        os.path.join(SITE, "data", "countries-110m.json"): "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json",
        os.path.join(RAW, "iso-codes.json"): "https://cdn.jsdelivr.net/npm/i18n-iso-countries@7.11.0/codes.json",
        os.path.join(vend, "d3.v7.min.js"): "https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js",
        os.path.join(vend, "topojson-client.min.js"): "https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js",
    }
    for path, url in assets.items():
        if os.path.exists(path) and not FORCE:
            continue
        with open(path, "wb") as f:
            f.write(http_bytes(url))
        print("  saved", os.path.relpath(path, ROOT))

    with open(os.path.join(RAW, "_fetched.json"), "w") as f:
        json.dump({"fetched_at": time.strftime("%Y-%m-%d")}, f)
    print("done")


if __name__ == "__main__":
    main()
