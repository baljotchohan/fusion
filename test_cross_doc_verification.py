"""
Adversarial Verification Suite for Phase 1.5
Asserts cross-document ARR discrepancies, timeframe-aware exclusions, and cap table contradictions.
"""

import sys
from core.diligence_engine import run_diligence_calculations

GRN = "\033[92m"; RED = "\033[91m"; RST = "\033[0m"; BLD = "\033[1m"
PASS = f"{GRN}✅ PASS{RST}"
FAIL = f"{RED}❌ FAIL{RST}"

results = {"pass": 0, "fail": 0}

def assert_true(expr, msg):
    if expr:
        results["pass"] += 1
        print(f"  {PASS}  {msg}")
    else:
        results["fail"] += 1
        print(f"  {FAIL}  {msg}")

def section(title):
    print(f"\n{BLD}{title}{RST}")
    print("-" * 60)

# Base mock data for test templates
base_pitch = {
    "company": {
        "name": {"value": "DiligenceCorp", "confidence": 100, "provenance": "direct"},
        "industry": {"value": "Enterprise SaaS", "confidence": 100, "provenance": "direct"},
        "stage": {"value": "Series A", "confidence": 100, "provenance": "direct"},
        "raise_amount": {"value": "$5,000,000", "confidence": 100, "provenance": "direct"},
        "post_money_valuation": {"value": "$25,000,000", "confidence": 100, "provenance": "direct"},
    },
    "financials": {
        "arr": {"value": "$12,000,000", "confidence": 95, "provenance": "direct"},
        "burn": {"value": "$300,000", "confidence": 95, "provenance": "direct"},
        "runway": {"value": "18", "confidence": 95, "provenance": "direct"},
        "gross_margin": {"value": "80%", "confidence": 95, "provenance": "direct"},
        "customers": {"value": "120", "confidence": 95, "provenance": "direct"},
        "customer_concentration": {"value": "10%", "confidence": 95, "provenance": "direct"},
        "red_flags": [],
    },
    "legal": {
        "litigation": {"value": "No active lawsuits.", "confidence": 95, "provenance": "direct"},
        "compliance": {"value": "Fully compliant.", "confidence": 95, "provenance": "direct"},
        "red_flags": [],
    },
    "technical": {
        "stack": {"value": "Go 1.22 + Postgres", "confidence": 95, "provenance": "direct"},
        "security": {"value": "SOC 2 Type II", "confidence": 95, "provenance": "direct"},
        "red_flags": [],
    },
    "market": {
        "tam": {"value": "$10B", "confidence": 95, "provenance": "direct"},
        "competition": {"value": "None direct.", "confidence": 95, "provenance": "direct"},
        "red_flags": [],
    }
}

def main():
    # ==============================================================================
    # TEST 1: Real Contradiction (ARR)
    # ==============================================================================
    section("Test 1 — Real ARR Contradiction")

    t1_pitch = dict(base_pitch)
    t1_pitch["document_text"] = (
        "--- DOCUMENT: pitch_deck.pdf ---\n"
        "We have current ARR of $12M.\n\n"
        "--- DOCUMENT: financials.xlsx ---\n"
        "Current ARR is $7M."
    )

    calc1 = run_diligence_calculations(t1_pitch)
    contradictions1 = calc1.get("contradictions", [])

    # Find ARR contradiction
    arr_contra = next((c for c in contradictions1 if c["type"] == "ARR" and c["doc_a"] != c["doc_b"]), None)

    assert_true(arr_contra is not None, "Detected ARR cross-document contradiction")
    if arr_contra:
        assert_true(arr_contra["severity"] == "Critical", f"Severity is Critical (got: {arr_contra['severity']})")
        assert_true(arr_contra["doc_a"] == "pitch_deck.pdf", "doc_a is pitch_deck.pdf")
        assert_true(arr_contra["doc_b"] == "financials.xlsx", "doc_b is financials.xlsx")
        assert_true(arr_contra["value_a"] == 12000000.0, "value_a is $12M")
        assert_true(arr_contra["value_b"] == 7000000.0, "value_b is $7M")
        assert_true(abs(arr_contra["difference_pct"] - 41.7) < 0.2, f"difference_pct is ~41.7% (got: {arr_contra['difference_pct']}%)")
        assert_true("🚨 Critical ARR Discrepancy" in arr_contra["message"], f"Message has Critical alert (got: {arr_contra['message']})")

    # ==============================================================================
    # TEST 2: Same Metric, Different Timeframe
    # ==============================================================================
    section("Test 2 — Same Metric, Different Timeframe")

    t2_pitch = dict(base_pitch)
    t2_pitch["document_text"] = (
        "--- DOCUMENT: pitch_deck.pdf ---\n"
        "Our current ARR is $7M.\n\n"
        "--- DOCUMENT: forecast.xlsx ---\n"
        "By FY2027 ARR will reach $28M."
    )

    calc2 = run_diligence_calculations(t2_pitch)
    contradictions2 = calc2.get("contradictions", [])
    arr_contradictions2 = [c for c in contradictions2 if c["type"] == "ARR"]

    assert_true(len(arr_contradictions2) == 0, "No ARR contradiction for different timeframes (current vs. FY27)")

    # ==============================================================================
    # TEST 3: Cap Table Conflict
    # ==============================================================================
    section("Test 3 — Cap Table Conflict")

    t3_pitch = dict(base_pitch)
    t3_pitch["document_text"] = (
        "--- DOCUMENT: cap_table.pdf ---\n"
        "Total outstanding shares is 15M shares.\n\n"
        "--- DOCUMENT: legal_disclosure.txt ---\n"
        "Outstanding shares is 17M shares."
    )

    calc3 = run_diligence_calculations(t3_pitch)
    contradictions3 = calc3.get("contradictions", [])

    # Find cap table contradiction
    cap_contra = next((c for c in contradictions3 if c["type"] == "Cap Table"), None)

    assert_true(cap_contra is not None, "Detected Cap Table cross-document contradiction")
    if cap_contra:
        assert_true(cap_contra["severity"] == "Material", f"Severity is Material (got: {cap_contra['severity']})")
        assert_true(cap_contra["doc_a"] == "cap_table.pdf", "doc_a is cap_table.pdf")
        assert_true(cap_contra["doc_b"] == "legal_disclosure.txt", "doc_b is legal_disclosure.txt")
        assert_true(cap_contra["value_a"] == 15000000, "value_a is 15M")
        assert_true(cap_contra["value_b"] == 17000000, "value_b is 17M")
        assert_true(abs(cap_contra["difference_pct"] - 11.8) < 0.2, f"difference_pct is ~11.8% (got: {cap_contra['difference_pct']}%)")
        assert_true("🚨 Material Cap Table Discrepancy" in cap_contra["message"], f"Message has Material alert (got: {cap_contra['message']})")

    # Print summary
    print("\n" + "=" * 60)
    print(f"VERIFICATION RESULTS: {results['pass']} passed, {results['fail']} failed")
    print("=" * 60)
    if results["fail"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
