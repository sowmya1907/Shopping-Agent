import re

def extract_price(text: str):
    match = re.search(r"₹\s?([\d,]+)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None
