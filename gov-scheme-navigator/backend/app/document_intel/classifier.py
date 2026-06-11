from __future__ import annotations

def classify_document(text: str) -> str:
    text_lower = text.lower()
    if "aadhaar" in text_lower or "uidai" in text_lower:
        return "Aadhaar"
    elif "income" in text_lower or "revenue" in text_lower:
        return "Income Certificate"
    elif "pan" in text_lower or "income tax" in text_lower:
        return "PAN"
    else:
        return "Unknown"
