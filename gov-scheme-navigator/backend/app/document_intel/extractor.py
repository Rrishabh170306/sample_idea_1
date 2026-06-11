from __future__ import annotations

from typing import Any
import re

def extract_entities(text: str, doc_type: str) -> dict[str, Any]:
    # Regex based mock of LLM extraction
    data = {}
    confidence = 0.9
    
    if doc_type == "Aadhaar":
        dob_match = re.search(r'(DOB|Year of Birth|YOB)[:\s]*([\d/]+)', text, re.IGNORECASE)
        if dob_match:
            data["age"] = 30 # Mock calculated age
        else:
            confidence = 0.5
            
    elif doc_type == "Income Certificate":
        inc_match = re.search(r'(₹|Rs\.?|Rupees)\s*([\d,]+)', text, re.IGNORECASE)
        if inc_match:
            data["income"] = float(inc_match.group(2).replace(",", ""))
        else:
            confidence = 0.6
            
    return {
        "extracted_data": data,
        "confidence": confidence
    }
