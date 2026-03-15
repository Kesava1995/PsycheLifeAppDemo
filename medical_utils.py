from datetime import datetime, timedelta
import re

def parse_duration(duration_text):
    """
    Parses a duration string (e.g., '2 weeks', '10 days') into a timedelta object.
    Returns None if parsing fails.
    """
    if not duration_text:
        return None
        
    text = duration_text.lower().strip()
    
    # Regex for number and unit
    match = re.search(r'(\d+)\s*(day|week|month|year)s?', text)
    if not match:
        return None
        
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'day':
        return timedelta(days=value)
    elif unit == 'week':
        return timedelta(weeks=value)
    elif unit == 'month':
        return timedelta(days=value * 30) # Approximate
    elif unit == 'year':
        return timedelta(days=value * 365)
        
    return None


def duration_to_days(duration_text):
    """
    Returns approximate number of days for a duration string (for sorting).
    Returns 0 if parsing fails.
    """
    delta = parse_duration(duration_text)
    return delta.days if delta else 0


def format_timedelta_as_duration(delta):
    """
    Formats a timedelta as human-readable duration (e.g. '3 months', '2 weeks').
    Uses singular form when value is 1.
    """
    if not delta or not hasattr(delta, 'days'):
        return ''
    days = delta.days
    if days <= 0:
        return ''
    if days >= 365:
        n = round(days / 365)
        return f"{n} year" if n == 1 else f"{n} years"
    if days >= 30:
        n = round(days / 30)
        return f"{n} month" if n == 1 else f"{n} months"
    if days >= 7:
        n = round(days / 7)
        return f"{n} week" if n == 1 else f"{n} weeks"
    return f"{days} day" if days == 1 else f"{days} days"


def calculate_start_date(duration_text, reference_date=None):
    """
    Calculates the start date by subtracting duration from the reference date.
    """
    if reference_date is None:
        reference_date = datetime.now()
        
    # Ensure reference_date is a datetime object if it's passed as date
    if hasattr(reference_date, 'strftime') and not hasattr(reference_date, 'hour'):
         reference_date = datetime.combine(reference_date, datetime.min.time())

    delta = parse_duration(duration_text)
    if delta:
        return reference_date - delta
    return None

def calculate_midpoint_date(start_date, end_date):
    """
    Calculates the date exactly between start_date and end_date.
    """
    # Ensure dates are datetime objects
    if hasattr(start_date, 'strftime') and not hasattr(start_date, 'hour'):
         start_date = datetime.combine(start_date, datetime.min.time())
    if hasattr(end_date, 'strftime') and not hasattr(end_date, 'hour'):
         end_date = datetime.combine(end_date, datetime.min.time())
        
    total_time = end_date - start_date
    midpoint_delta = total_time / 2
    return start_date + midpoint_delta

def get_unified_dose(drug_name, dose_mg):
    """
    Returns raw numeric dose (mg) from dose_mg string. Used where RTP is not applied.
    """
    try:
        if not dose_mg:
            return 0.0
        match = re.search(r"[-+]?\d*\.\d+|\d+", str(dose_mg))
        return float(match.group()) if match else 0.0
    except Exception:
        return 0.0


def _frequency_to_daily_multiplier(frequency):
    """Convert frequency code (e.g. '1-0-1', '1-1-1') to daily multiplier (times per day)."""
    if not frequency:
        return 1
    s = str(frequency).strip()
    if not s or s.upper() == "SOS":
        return 1
    total = 0
    for part in re.split(r"[\s\-]+", s):
        part = part.strip()
        if not part:
            continue
        if part in ("½", "1/2", "0.5"):
            total += 0.5
        elif part in ("¼", "1/4", "0.25"):
            total += 0.25
        else:
            try:
                total += float(part)
            except ValueError:
                pass
    return max(1, total) if total > 0 else 1


def compute_med_chart_value(drug_name, dose_mg, frequency, norm_mode="rtp"):
    """
    For chart representation: compute normalized Y (RTP % or equivalent) and actual dose label.
    RTP = (Current dose – min) / (max – min) * 100 so each drug sits in 0–100% of its range.
    On hover/click the UI should show actual_dose_label (what the doctor entered), not the Y value.

    Returns:
        (y_value, actual_dose_label)
        - y_value: float for chart Y (RTP 0–100, or CPZ/Diazepam equivalent mg when norm_mode is 'equivalent')
        - actual_dose_label: string e.g. "10 mg (1-0-1)" for tooltips/modals
    """
    try:
        from dose_data import get_dose_info, get_rtp, get_rti, get_cpz_equivalent_mg, get_diazepam_equivalent_mg
    except ImportError:
        match = re.search(r"[-+]?\d*\.\d+|\d+", str(dose_mg))
        raw = float(match.group()) if dose_mg and match else 0.0
        lbl = f"{dose_mg or ''} ({frequency or ''})".strip().rstrip("()").strip()
        return (raw, lbl or f"{raw} mg")

    raw_mg = get_unified_dose(drug_name, dose_mg)
    if raw_mg is None or raw_mg <= 0:
        lbl = f"{dose_mg or ''} ({frequency or ''})".strip().rstrip("()").strip()
        return (0.0, lbl or "—")

    mult = _frequency_to_daily_multiplier(frequency)
    daily_mg = raw_mg * mult
    freq_str = (frequency or "").strip()
    if freq_str:
        actual_dose_label = f"{dose_mg or ''} ({freq_str})".strip()
    else:
        # dose_mg may be float from DB; ensure we have a string before .strip()
        actual_dose_label = str(dose_mg if (dose_mg not in (None, '')) else f"{raw_mg} mg").strip()
    if not actual_dose_label:
        actual_dose_label = f"{raw_mg} mg"

    if norm_mode == "equivalent":
        info = get_dose_info(drug_name)
        category = (info or {}).get("category", "other")
        if category == "benzodiazepine":
            eq = get_diazepam_equivalent_mg(drug_name, daily_mg)
            return (eq if eq is not None else raw_mg, actual_dose_label)
        if category in ("other",) or info:
            cpz = get_cpz_equivalent_mg(drug_name, daily_mg)
            if cpz is not None:
                return (cpz, actual_dose_label)
        rtp_val, _, _ = get_rtp(drug_name, daily_mg)
        return (rtp_val if rtp_val is not None else raw_mg, actual_dose_label)

    # Benzodiazepines: RTI = (Equivalent Dose - 2.5) * 100 / 50 (diazepam equivalent)
    # Others: RTP = (Current dose - min) * 100 / (max - min)
    info = get_dose_info(drug_name)
    if info and (info.get("category") == "benzodiazepine"):
        rti_val = get_rti(drug_name, daily_mg)
        if rti_val is not None:
            return (rti_val, actual_dose_label)
    rtp_percent, min_mg, max_mg = get_rtp(drug_name, daily_mg)
    if rtp_percent is not None:
        return (round(rtp_percent, 1), actual_dose_label)
    return (raw_mg, actual_dose_label)

# --- PRESCRIPTION LANGUAGE CONVERTER (Positional logic) ---
def format_frequency(code):
    """
    Parses frequency codes and converts to descriptive text.
    e.g., '1-0-1-1-1' -> 'One in Dawn, One in Afternoon, One in Evening & One in Night'
    """
    if not code: return ""
    code = str(code).strip()

    if '-' not in code and not code.isdigit():
        return code

    parts = code.split('-')
    count = len(parts)

    mappings = {
        2: ["Morning", "Night"],
        3: ["Morning", "Afternoon", "Night"],
        4: ["Morning", "Afternoon", "Evening", "Night"],
        5: ["Dawn", "Morning", "Afternoon", "Evening", "Night"]
    }

    if count not in mappings:
        return code

    time_slots = mappings[count]
    output_parts = []
    
    # Map numbers and fractions to capitalized words
    qty_map = {
        '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five',
        '0.5': 'Half', '1/2': 'Half', '½': 'Half',
        '0.25': 'Quarter', '1/4': 'Quarter', '¼': 'Quarter'
    }

    for i, val in enumerate(parts):
        val = val.strip()
        if val == '0' or not val:
            continue

        qty_str = qty_map.get(val, val)
        output_parts.append(f"{qty_str} in {time_slots[i]}")

    if not output_parts:
        return ""
        
    if len(output_parts) == 1:
        return output_parts[0]
        
    # Join all but the last with commas, and the very last with ' & '
    return ", ".join(output_parts[:-1]) + " & " + output_parts[-1]


# --- SCALE ASSESSMENT SCORING (CIWA-Ar, Y-BOCS) ---

def calculate_ciwa_ar(responses):
    """
    Calculates CIWA-Ar score and severity.
    :param responses: Dictionary of integer values for the 10 questions (e.g. {'q1': 7, 'q2': 4, ...})
    """
    total_score = sum(int(val) for val in responses.values())

    if total_score <= 9:
        severity = "Absent or minimal withdrawal"
    elif 10 <= total_score <= 19:
        severity = "Mild to moderate withdrawal"
    else:
        severity = "Severe withdrawal"

    return total_score, severity


def calculate_ybocs(responses):
    """
    Calculates Y-BOCS score and severity.
    :param responses: Dictionary of integer values for the 10 questions
    """
    total_score = sum(int(val) for val in responses.values())

    if total_score <= 7:
        severity = "Subclinical"
    elif 8 <= total_score <= 15:
        severity = "Mild OCD"
    elif 16 <= total_score <= 23:
        severity = "Moderate OCD"
    elif 24 <= total_score <= 31:
        severity = "Severe OCD"
    else:
        severity = "Extreme OCD"

    return total_score, severity


def process_scale_submission(scale_id, responses):
    """
    Main router for scale calculations to be called from your Flask route.
    """
    if scale_id == "CIWA-Ar":
        return calculate_ciwa_ar(responses)
    elif scale_id == "Y-BOCS":
        return calculate_ybocs(responses)
    else:
        raise ValueError(f"Unknown Scale ID: {scale_id}")
