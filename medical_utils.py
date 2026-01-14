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
    Currently returns the dose as a float, but can be expanded 
    to convert different drugs to a standard equivalent if needed.
    """
    try:
        return float(dose_mg)
    except (ValueError, TypeError):
        return 0.0
