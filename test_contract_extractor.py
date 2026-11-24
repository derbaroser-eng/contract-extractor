#!/usr/bin/env python3
"""
test_contract_extractor.py — failing tests for contract-extractor.

Run: python workspace/products/contract-extractor/test_contract_extractor.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "extract.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, cond, detail))


def run_extract(payload: dict) -> dict:
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if r.returncode != 0:
        return {"error": f"exit={r.returncode}", "stderr": r.stderr[:200]}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid_json", "stdout": r.stdout[:200]}


def base_text():
    return ("This Agreement is between Acme Corp and Beta Inc. "
            "Product: Pro Plan. Payment: Monthly. Price: $29/month. "
            "Term: 12 months starting 2026-01-01. Renewal: automatic.")


# --- test 1: product extraction ---
out = run_extract({"text": base_text()})
check("product: extracted", isinstance(out, dict) and out.get("product") == "Pro Plan", str(out)[:100])

# --- test 2: payment schedule ---
check("schedule: monthly", out.get("payment_schedule") == "monthly", str(out))

# --- test 3: price ---
check("price: 29", out.get("price") == 29.0, str(out))

# --- test 4: currency ---
check("currency: usd", out.get("currency") == "usd", str(out))

# --- test 5: term ---
check("term: 12", out.get("term_months") == 12, str(out))

# --- test 6: start date ---
check("start_date: 2026-01-01", out.get("start_date") == "2026-01-01", str(out))

# --- test 7: renewal ---
check("renewal: automatic", out.get("renewal") == "automatic", str(out))

# --- test 8: EUR currency ---
out = run_extract({"text": "Product: Basic. Price: 49 EUR. Payment: Annual."})
check("eur: currency", out.get("currency") == "eur", str(out))
check("eur: price", out.get("price") == 49.0, str(out))
check("annual: schedule", out.get("payment_schedule") == "annual", str(out))

# --- test 9: quarterly ---
out = run_extract({"text": "Payment: Quarterly. Price: $99."})
check("quarterly: schedule", out.get("payment_schedule") == "quarterly", str(out))

# --- test 10: year → months conversion ---
out = run_extract({"text": "Term: 1 year. Product: X."})
check("year: term_months=12", out.get("term_months") == 12, str(out))

# --- test 11: manual renewal ---
out = run_extract({"text": "Renewal: manual. Product: Y."})
check("manual: renewal", out.get("renewal") == "manual", str(out))

# --- test 12: missing product ---
out = run_extract({"text": "Price: $10. Payment: Monthly."})
check("missing: product null", out.get("product") is None, str(out))

# --- test 13: no fields found → exit 2 ---
r = subprocess.run(
    [sys.executable, str(SCRIPT)],
    input=json.dumps({"text": "Hello world, nothing here."}),
    capture_output=True, text=True, timeout=10,
)
check("nofields: exit 2", r.returncode == 2, f"rc={r.returncode}")

# --- test 14: invalid input (missing text) ---
r = subprocess.run(
    [sys.executable, str(SCRIPT)],
    input=json.dumps({"foo": "bar"}),
    capture_output=True, text=True, timeout=10,
)
check("invalid: exit 1", r.returncode == 1, f"rc={r.returncode}")

# --- test 15: invalid input (non-string text) ---
r = subprocess.run(
    [sys.executable, str(SCRIPT)],
    input=json.dumps({"text": 123}),
    capture_output=True, text=True, timeout=10,
)
check("wrongtype: exit 1", r.returncode == 1, f"rc={r.returncode}")

# --- test 16: no secrets in output ---
secret_input = "Product: SecretPlan. Price: $100. Internal note: do not leak this."
out = run_extract({"text": secret_input})
if isinstance(out, dict):
    check("no secrets: full input not echoed", secret_input not in json.dumps(out), str(out))
    check("no secrets: internal note not in output", "do not leak this" not in json.dumps(out), str(out))

# --- test 17: deterministic ---
out1 = run_extract({"text": base_text()})
out2 = run_extract({"text": base_text()})
check("deterministic: same output", out1 == out2, f"{out1} vs {out2}")

# --- test 18: EUR symbol prefix (real-world EU contract) ---
out = run_extract({"text": "Product: Basic. Price: EUR 49.00. Payment: Annual. Note: 49."})
out_sym = run_extract({"text": "Product: Basic. Price: €49.00. Payment: Annual."})
check("euro symbol prefix: currency", out_sym.get("currency") == "eur", str(out_sym))
check("euro symbol prefix: price", out_sym.get("price") == 49.0, str(out_sym))

# --- test 19: EUR symbol suffix (common EU invoice layout) ---
out_suf = run_extract({"text": "Product: Basic. Price: 49 €. Payment: Annual."})
check("euro symbol suffix: price", out_suf.get("price") == 49.0, str(out_suf))

# --- test 20: european number format (EU contracts use dot thousands, comma decimals) ---
out_eu = run_extract({"text": "Product: Pro. Price: €1.234,56. Payment: Annual."})
check("european number format: price", out_eu.get("price") == 1234.56, str(out_eu))
out_us = run_extract({"text": "Product: Pro. Price: $1,234.56. Payment: Annual."})
check("us number format: price", out_us.get("price") == 1234.56, str(out_us))

# --- report ---
passed = sum(1 for _, ok, _ in results if ok)
failed = [(n, d) for n, ok, d in results if not ok]
print(f"\n{passed}/{len(results)} assertions passed")
if failed:
    print("\nFAILED:")
    for n, d in failed:
        print(f"  {n}  ({d})")
    sys.exit(1)
print("ALL TESTS GREEN")
