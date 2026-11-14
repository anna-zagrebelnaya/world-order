# World Order Monitor

Static website that places every country on the big cycles from Ray Dalio's
*Principles for Dealing with the Changing World Order*: the debt cycle, internal order and
external order, plus the empire arc and the 18 determinants of power. Everything is
computed from public data (World Bank, IMF, SIPRI, FAS, GFCI, COFER, SWIFT).

- **Site:** `site/index.html`. Pure static files that also work from `file://`.
- **Spec & method:** [`SPEC.md`](SPEC.md)
- **Curated research inputs + research date:** `research/curated.json`

## New edition
```bash
# 1. edit research/curated.json (research_date, COFER/SWIFT/GFCI/FAS, wars, Dalio quotes)
python3 scripts/fetch_data.py --force   # download fresh public data into data/raw/
python3 scripts/build_data.py           # recompute → site/data/data.js
```

An independent visualisation. It is not affiliated with Ray Dalio or Bridgewater.
