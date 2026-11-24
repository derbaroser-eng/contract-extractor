#!/usr/bin/env python3
"""
extract.py — deterministic contract field extractor.

Reads JSON from stdin, writes JSON to stdout.
No external calls, no file I/O, no secrets in output.
"""
import json
import re
import sys


def extract_product(text):
    m = re.search(r"(?:Product|Plan|Service)\s*:\s*([^.\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_schedule(text):
    if re.search(r"\bmonthly\b", text, re.IGNORECASE):
        return "monthly"
    if re.search(r"\bquarterly\b", text, re.IGNORECASE):
        return "quarterly"
    if re.search(r"\b(annual|annually|yearly)\b", text, re.IGNORECASE):
        return "annual"
    return None


def _num(raw: str):
    """Parse a number with US (1,234.56) or EU (1.234,56) separators."""
    s = raw.strip().rstrip(",.")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):      # EU: dot thousands, comma decimal
            s = s.replace(".", "").replace(",", ".")
        else:                                 # US: comma thousands, dot decimal
            s = s.replace(",", "")
    elif "," in s:                            # comma only: 2 trailing digits = decimal
        s = s.replace(",", ".") if len(s) - s.rfind(",") - 1 == 2 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def extract_price(text):
    m = re.search(r"(?:\$|€)\s*([\d][\d.,]*)", text)
    if m:
        return _num(m.group(1))
    m = re.search(r"([\d][\d.,]*)\s*(?:USD|EUR|€)", text, re.IGNORECASE)
    if m:
        return _num(m.group(1))
    return None


def extract_currency(text):
    if re.search(r"\$|USD", text, re.IGNORECASE):
        return "usd"
    if re.search(r"€|EUR", text, re.IGNORECASE):
        return "eur"
    return None


def extract_term(text):
    m = re.search(r"(\d+)\s*months?", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*years?", text, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 12
    return None


def extract_start_date(text):
    m = re.search(r"(?:starting|effective|beginning)\s+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    return m.group(1) if m else None


def extract_renewal(text):
    if re.search(r"\b(automatic|auto-renew)\b", text, re.IGNORECASE):
        return "automatic"
    if re.search(r"\b(manual|non-renewing)\b", text, re.IGNORECASE):
        return "manual"
    return None


def extract_fields(text):
    return {
        "product": extract_product(text),
        "payment_schedule": extract_schedule(text),
        "price": extract_price(text),
        "currency": extract_currency(text),
        "term_months": extract_term(text),
        "start_date": extract_start_date(text),
        "renewal": extract_renewal(text),
    }


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("error: invalid JSON", file=sys.stderr)
        return 1

    if not isinstance(data, dict) or "text" not in data:
        print("error: missing 'text' field", file=sys.stderr)
        return 1

    if not isinstance(data["text"], str):
        print("error: 'text' must be a string", file=sys.stderr)
        return 1

    result = extract_fields(data["text"])

    if all(v is None for v in result.values()):
        print("error: no fields found in contract text", file=sys.stderr)
        return 2

    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
