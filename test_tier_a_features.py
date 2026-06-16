"""
Verification Suite for Tier A Diligence Features
Asserts Document/Founder Credibility split, weighted IC Readiness,
customer concentration survival tiers, structured warnings, and owner-based action priorities.
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
        "name": {"value": "DiligenceCorp", "confidence": 100, "provenance": "direct", "evidence": "name is DiligenceCorp"},
        "industry": {"value": "Enterprise SaaS", "confidence": 100, "provenance": "direct", "evidence": "industry is SaaS"},
        "stage": {"value": "Series A", "confidence": 100, "provenance": "direct", "evidence": "stage is Series A"},
        "raise_amount": {"value": "$5,000,000", "confidence": 100, "provenance": "direct", "evidence": "raising $5M"},
        "post_money_valuation": {"value": "$25,000,000", "confidence": 100, "provenance": "direct", "evidence": "valuation is $25M"},
    },
    "financials": {
        "arr": {"value": "$12,000,000", "confidence": 95, "provenance": "direct", "evidence": "ARR is $12M"},
        "burn": {"value": "$300,000", "confidence": 95, "provenance": "direct", "evidence": "burn is $300k"},
        "runway": {"value": "18", "confidence": 95, "provenance": "direct", "evidence": "runway is 18"},
        "gross_margin": {"value": "80%", "confidence": 95, "provenance": "direct", "evidence": "gross margin is 80%"},
        "customers": {"value": "120", "confidence": 95, "provenance": "direct", "evidence": "120 customers"},
        "customer_concentration": {"value": "10%", "confidence": 95, "provenance": "direct", "evidence": "10% concentration"},
        "red_flags": [],
    },
    "legal": {
        "litigation": {"value": "No active lawsuits.", "confidence": 95, "provenance": "direct", "evidence": "no litigation"},
        "compliance": {"value": "Fully compliant.", "confidence": 95, "provenance": "direct", "evidence": "fully compliant"},
        "red_flags": [],
    },
    "technical": {
        "stack": {"value": "Go 1.22 + Postgres", "confidence": 95, "provenance": "direct", "evidence": "Go 1.22 backend"},
        "security": {"value": "SOC 2 Type II", "confidence": 95, "provenance": "direct", "evidence": "SOC 2 certified"},
        "red_flags": [],
    },
    "market": {
        "tam": {"value": "$10B", "confidence": 95, "provenance": "direct", "evidence": "TAM is $10B"},
        "competition": {"value": "None direct.", "confidence": 95, "provenance": "direct", "evidence": "no direct competitors"},
        "red_flags": [],
    }
}

def main():
    # ==============================================================================
    # TEST 1: Clean Deal (Perfect Credibility & Readiness)
    # ==============================================================================
    section("Test 1 — Clean Deal Credibility & Readiness")

    t1_pitch = dict(base_pitch)
    t1_pitch["document_text"] = "A clean SaaS startup with ARR of $12M and stable market conditions."

    calc1 = run_diligence_calculations(t1_pitch)

    assert_true(calc1["document_credibility_score"] == 100.0, "Clean document yields 100% Document Credibility")
    assert_true(calc1["founder_credibility_score"] == 100.0, "Clean document yields 100% Founder Credibility")
    assert_true(calc1["data_room_completeness"] == 100.0, "All 10 core fields populated yields 100% Completeness")
    assert_true(calc1["ic_readiness_score"] == 100.0, "Zero gaps and zero contradictions yields 100% IC Readiness")
    assert_true(calc1["deal_readiness_status"] == "Ready for IC Review", "Clean deal is Ready for IC Review")

    # ==============================================================================
    # TEST 2: Weighted IC Readiness (Severity Deductions)
    # ==============================================================================
    section("Test 2 — Weighted IC Readiness Scoring")

    # 2a. Minor Contradiction
    t2a_pitch = dict(base_pitch)
    t2a_pitch["document_text"] = (
        "--- DOCUMENT: pitch.pdf ---\n"
        "ARR is $12M.\n\n"
        "--- DOCUMENT: financials.xlsx ---\n"
        "ARR is $12.1M." # <2% difference -> Minor
    )
    calc2a = run_diligence_calculations(t2a_pitch)
    assert_true(calc2a["ic_readiness_score"] == 97.0, f"Minor contradiction drops readiness by 3 points (got: {calc2a['ic_readiness_score']})")
    assert_true(calc2a["document_credibility_score"] == 97.0, "Document Credibility drops by 3 points")

    # 2b. Critical Contradiction
    t2b_pitch = dict(base_pitch)
    t2b_pitch["document_text"] = (
        "--- DOCUMENT: pitch.pdf ---\n"
        "ARR is $12M.\n\n"
        "--- DOCUMENT: financials.xlsx ---\n"
        "ARR is $7M." # >25% difference -> Critical
    )
    calc2b = run_diligence_calculations(t2b_pitch)
    assert_true(calc2b["ic_readiness_score"] == 75.0, f"Critical contradiction drops readiness by 25 points (got: {calc2b['ic_readiness_score']})")

    # ==============================================================================
    # TEST 3: Document vs Founder Credibility Separation
    # ==============================================================================
    section("Test 3 — Credibility Separation")

    t3_pitch = dict(base_pitch)
    # We will inject a minor parsing discrepancy but also an SEC investigation flag
    t3_pitch["document_text"] = (
        "--- DOCUMENT: pitch.pdf ---\n"
        "ARR is $12M.\n"
        "Note: Regulatory agency opened an SEC investigation against prior token sales.\n\n"
        "--- DOCUMENT: financials.xlsx ---\n"
        "ARR is $12.1M."
    )

    calc3 = run_diligence_calculations(t3_pitch)
    # Minor contradiction = -3 to Document Credibility (97)
    # SEC Investigation = -40 to Founder Credibility (60)
    assert_true(calc3["document_credibility_score"] == 97.0, f"Document Credibility is 97 (got: {calc3['document_credibility_score']})")
    assert_true(calc3["founder_credibility_score"] == 60.0, f"Founder Credibility is 60 (got: {calc3['founder_credibility_score']})")

    # ==============================================================================
    # TEST 4: Survival Classifications & Structured Warnings
    # ==============================================================================
    section("Test 4 — Survival Classes & Structured Warnings")

    import copy
    t4_pitch = copy.deepcopy(base_pitch)
    t4_pitch["financials"]["customer_concentration"] = {"value": "80%", "confidence": 95, "provenance": "direct", "evidence": "80% customer concentration"}
    t4_pitch["financials"]["runway"] = {"value": "2", "confidence": 95, "provenance": "direct", "evidence": "2 months runway"}
    t4_pitch["document_text"] = "High customer concentration of 80%. Critical runway is 2 months."

    calc4 = run_diligence_calculations(t4_pitch)
    survival = calc4["scenario"].get("survival_classification") if calc4.get("scenario") else None

    assert_true(survival == "Critical", f"Survival classification for runway < 3 months is Critical (got: {survival})")

    # Check structured audit warning shape
    warnings = calc4.get("financial_audit_warnings", [])
    concentration_warn = next((w for w in warnings if w["type"] == "Concentration Risk"), None)
    runway_warn = next((w for w in warnings if w["type"] == "Runway Masking"), None)

    assert_true(concentration_warn is not None, "Concentration warning generated")
    if concentration_warn:
        assert_true(concentration_warn["severity"] == "Medium", "Concentration warning severity is Medium")
        assert_true(concentration_warn["confidence"] == 95, "Concentration warning confidence is 95")
        assert_true(concentration_warn["evidence_refs"] == ["Financials"], "Evidence references financials")

    assert_true(runway_warn is not None, "Critical runway warning generated")
    if runway_warn:
        assert_true(runway_warn["severity"] == "High", "Runway warning severity is High")

    # ==============================================================================
    # TEST 5: Diligence Priority List
    # ==============================================================================
    section("Test 5 — Diligence Priority Checklist")

    priorities = calc4.get("diligence_priorities", [])
    high_pri = [p for p in priorities if p["priority"] == "High"]
    med_pri = [p for p in priorities if p["priority"] == "Medium"]

    # Runway < 3 is High priority, owned by CFO
    cfo_item = next((p for p in high_pri if p["owner"] == "CFO"), None)
    assert_true(cfo_item is not None, "CFO is assigned the critical runway priority")
    if cfo_item:
        assert_true("runway" in cfo_item["action"].lower(), "Action item targets runway resolution")

    # Concentration > 50% is Medium priority, owned by CEO
    ceo_item = next((p for p in med_pri if p["owner"] == "CEO"), None)
    assert_true(ceo_item is not None, "CEO is assigned the concentration priority")

    # Print summary
    print("\n" + "=" * 60)
    print(f"TIER A VERIFICATION RESULTS: {results['pass']} passed, {results['fail']} failed")
    print("=" * 60)
    if results["fail"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
