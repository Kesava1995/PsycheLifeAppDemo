"""
RDI and Equivalent Doses: RTP (Relative Therapeutic Percentage) and
Chlorpromazine/Diazepam equivalents for medication chart representation.
Data loaded from client Excel; fallback built-in tables for antipsychotics/benzos.
"""

import os
import re

# Default path to client Excel (relative to project root or absolute)
EXCEL_PATH = os.environ.get(
    "RDI_EXCEL_PATH",
    os.path.join(os.path.dirname(__file__), "..", "RDI and Equivalent Doses", "RDI and Equivalent Doses.xlsx")
)

# Built-in: Chlorpromazine equivalent doses (mg per day = 100 mg CPZ). Consensus values.
# Source: Table 1.4 (FGAs) and Table 1.5 (SGAs) - approximate equivalent doses.
CPZ_EQUIVALENTS = {
    "chlorpromazine": 100,
    "flupentixol": 3,
    "fluphenazine": 2,
    "haloperidol": 2,
    "pericyazine": 10,
    "perphenazine": 10,
    "pimozide": 2,
    "sulpiride": 200,
    "trifluoperazine": 5,
    "zuclopenthixol": 25,
    "amisulpride": 400,
    "aripiprazole": 15,
    "aripiprazole (as adjuvant)": 7.5,
    "asenapine": 10,
    "brexpiprazole": 2,
    "cariprazine": 1.5,
    "clozapine": 300,
    "iloperidone": 12,
    "lurasidone": 80,
    "olanzapine": 10,
    "olanzepine": 10,
    "quetiapine": 400,
    "quetiapine (as sedative)": 75,
    "risperidone": 4,
    "sertindole": 10,
}

# Built-in: Diazepam equivalent (mg per day = 10 mg diazepam).
# From client Excel: 10mg diazepam = 25 chlordiazepoxide = 2 lorazepam = 0.5 alprazolam = 0.5 clonazepam
DIAZEPAM_EQUIVALENTS = {
    "diazepam": 10,
    "chlordiazepoxide": 25,
    "lorazepam": 2,
    "alprazolam": 0.5,
    "clonazepam": 0.5,
}

# In-memory cache: drug name (normalized) -> { min_mg, max_mg, category }
_rtp_cache = None


def _norm_name(name):
    if not name:
        return ""
    return re.sub(r"\s+", " ", str(name).strip()).lower()


def _parse_mg(val):
    """Extract numeric mg from strings like '10mg', '20mg/day', '30md/day'."""
    if val is None:
        return None
    s = str(val).strip()
    match = re.search(r"[-+]?\d*\.?\d+", s)
    return float(match.group()) if match else None


def _load_excel():
    global _rtp_cache
    if _rtp_cache is not None:
        return _rtp_cache
    _rtp_cache = {}
    try:
        import openpyxl
        if os.path.isfile(EXCEL_PATH):
            wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
            ws = wb.active
            category = None
            for row in ws.iter_rows(values_only=True):
                if not row:
                    continue
                c1, c2, c3, c4 = (row[0], row[1], row[2] if len(row) > 2 else None, row[3] if len(row) > 3 else None)
                name = (c2 or "").strip() if isinstance(c2, str) else None
                if not name or name.lower().startswith("drug name") or name == "mg/day":
                    if c3 and "benzodiazepam" in str(c3).lower():
                        category = "benzodiazepine"
                    continue
                if c3 and "equivalent" in str(c3).lower() and "dose" in str(c3).lower():
                    continue
                min_mg = _parse_mg(c3)
                max_mg = _parse_mg(c4)
                if min_mg is not None and max_mg is not None and name and category != "benzodiazepine":
                    key = _norm_name(name)
                    _rtp_cache[key] = {"min_mg": min_mg, "max_mg": max_mg, "category": category or "other"}
                elif min_mg is not None and name and category == "benzodiazepine":
                    key = _norm_name(name)
                    if key not in DIAZEPAM_EQUIVALENTS:
                        DIAZEPAM_EQUIVALENTS[key] = min_mg
                    # RTP range for benzos comes from fallback, not from Excel equivalent column
            wb.close()
    except Exception:
        pass
    _build_fallback_rtp()
    return _rtp_cache


def _build_fallback_rtp():
    """Merge fallback RTP ranges for drugs not in Excel."""
    global _rtp_cache
    fallback = {
        "risperidone": (2, 16, "other"),
        "olanzapine": (5, 20, "other"),
        "olanzepine": (5, 20, "other"),
        "haloperidol": (2, 20, "other"),
        "aripiprazole": (10, 30, "other"),
        "aripiprazole (as adjuvant)": (2.5, 10, "other"),
        "amisulpride": (300, 1200, "other"),
        "clozapine": (6.25, 900, "other"),
        "chlorpromazine": (200, 1000, "other"),
        "cariprazine": (1.5, 6, "other"),
        "quetiapine": (150, 800, "other"),
        "quetiapine (as sedative)": (25, 150, "other"),
        "lithium carbonate": (150, 1800, "other"),
        "sodium valproate": (200, 3000, "other"),
        "carbamazepine": (100, 1600, "other"),
        "escitalopram": (10, 30, "other"),
        "fluoxetine": (20, 80, "other"),
        "fluoxamine": (50, 300, "other"),
        "sertraline": (50, 200, "other"),
        "paroxetine": (20, 62.5, "other"),
        "bupropion": (150, 450, "other"),
        "duloxetine": (60, 120, "other"),
        "venlafaxine": (75, 375, "other"),
        "vortioxetine": (10, 20, "other"),
        "diazepam": (2, 40, "benzodiazepine"),
        "chlordiazepoxide": (5, 100, "benzodiazepine"),
        "lorazepam": (0.5, 10, "benzodiazepine"),
        "alprazolam": (0.25, 4, "benzodiazepine"),
        "clonazepam": (0.25, 4, "benzodiazepine"),
    }
    for name, tup in fallback.items():
        mn, mx = tup[0], tup[1]
        cat = tup[2] if len(tup) > 2 else "other"
        key = _norm_name(name)
        if key not in _rtp_cache:
            _rtp_cache[key] = {"min_mg": mn, "max_mg": mx, "category": cat}


def get_dose_info(drug_name):
    """Return { min_mg, max_mg, category } for RTP, or None if unknown."""
    _load_excel()
    key = _norm_name(drug_name)
    return _rtp_cache.get(key)


def get_rtp(drug_name, daily_dose_mg):
    """
    RTP = (Current dose – min therapeutic dose) * 100 / (Max therapeutic dose – min therapeutic dose).
    Returns (rtp_percent, min_mg, max_mg). rtp_percent can be < 0 or > 100 if outside range.
    """
    info = get_dose_info(drug_name)
    if not info or daily_dose_mg is None:
        return (None, None, None)
    min_mg = info["min_mg"]
    max_mg = info["max_mg"]
    denom = max_mg - min_mg
    if denom <= 0:
        return (50.0, min_mg, max_mg)
    rtp = (float(daily_dose_mg) - min_mg) * 100.0 / denom
    return (round(rtp, 1), min_mg, max_mg)


def get_rti(drug_name, daily_dose_mg):
    """
    For benzodiazepines only: RTI = (Equivalent Dose - 2.5) * 100 / 50.
    Equivalent dose is in diazepam equivalent (mg). Returns RTI percent or None if not a benzo.
    """
    eq_mg = get_diazepam_equivalent_mg(drug_name, daily_dose_mg)
    if eq_mg is None:
        return None
    rti = (float(eq_mg) - 2.5) * 100.0 / 50.0
    return round(rti, 1)


def get_cpz_equivalent_mg(drug_name, daily_dose_mg):
    """Convert daily dose to chlorpromazine equivalent mg (100 mg CPZ = 1 unit)."""
    key = _norm_name(drug_name)
    equiv = CPZ_EQUIVALENTS.get(key)
    if equiv is None or not daily_dose_mg or daily_dose_mg <= 0:
        return None
    return round((float(daily_dose_mg) / equiv) * 100, 1)


def get_diazepam_equivalent_mg(drug_name, daily_dose_mg):
    """Convert daily dose to diazepam equivalent mg (10 mg diazepam = 1 unit)."""
    key = _norm_name(drug_name)
    equiv = DIAZEPAM_EQUIVALENTS.get(key)
    if equiv is None or not daily_dose_mg or daily_dose_mg <= 0:
        return None
    return round((float(daily_dose_mg) / equiv) * 10, 1)
