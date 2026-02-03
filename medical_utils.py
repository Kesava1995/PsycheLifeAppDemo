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
    Parses frequency codes based on the number of segments (digits separated by hyphens).
    0 = Omit, 1+ = Quantity.
    """
    if not code: return ""
    code = str(code).strip()

    # If it's a legacy code (e.g. SOS) or just text, return as is
    if '-' not in code and not code.isdigit():
        return code

    parts = code.split('-')
    count = len(parts)

    # Define time slots based on the number of 'boxes'
    mappings = {
        2: ["Morning", "Night"],
        3: ["Morning", "Afternoon", "Night"],
        4: ["Morning", "Afternoon", "Evening", "Night"],
        5: ["Dawn", "Morning", "Afternoon", "Evening", "Night"]
    }

    # Fallback for unsupported lengths (e.g. 1 or >=6)
    if count not in mappings:
        return code

    time_slots = mappings[count]
    output_parts = []

    # Simple number-to-word map
    qty_map = {'1': 'One', '2': 'Two', '3': 'Three', '0.5': 'Half', '1/2': 'Half'}

    for i, val in enumerate(parts):
        val = val.strip()
        if val == '0' or not val:
            continue

        qty = qty_map.get(val, val)  # Use word if known, else number
        time = time_slots[i]
        output_parts.append(f"{qty} in {time}")

    if not output_parts:
        return ""

    if len(output_parts) == 1:
        return output_parts[0]

    return ", ".join(output_parts[:-1]) + " & " + output_parts[-1]
