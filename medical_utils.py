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
    Normalizes medication doses for visualization.
    """
    try:
        if not dose_mg: return 0.0
        # Extract first number found
        match = re.search(r"[-+]?\d*\.\d+|\d+", str(dose_mg))
        return float(match.group()) if match else 0.0
    except:
        return 0.0

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
