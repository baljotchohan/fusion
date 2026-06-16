"""
Live engine stress-test: 3 distinct, complicated companies pushed through the
REAL deterministic diligence engine (core/diligence_engine.run_diligence_calculations).
No mocks of the scorer — this is the exact code path the agents and mock-LLM use.
"""
import json
from core.diligence_engine import run_diligence_calculations

# ─────────────────────────────────────────────────────────────────────────────
# COMPANY A — "Helios Robotics" : genuinely STRONG deal. Should be INVEST.
#   Long runway, fat margins, diversified customers, no litigation, modern secure
#   stack, growing market. Tests that the engine does NOT reflexively reject.
# ─────────────────────────────────────────────────────────────────────────────
helios = {
    "company": {
        "name": "Helios Robotics",
        "industry": "Industrial Automation / Warehouse Robotics",
        "stage": "Series B",
        "raise_amount": "$25,000,000",
        "post_money_valuation": "$140,000,000",
    },
    "financials": {
        "arr_raw": 18000000,
        "monthly_burn_usd": 600000,
        "runway_months": 26,
        "gross_margin_pct": 71,
        "customer_revenue_breakdown": [
            {"customer": "DHL", "revenue_pct": 22},
            {"customer": "Maersk", "revenue_pct": 19},
            {"customer": "FedEx Ground", "revenue_pct": 17},
            {"customer": "Regional 3PLs (40 accounts)", "revenue_pct": 28},
            {"customer": "Long-tail SMB", "revenue_pct": 14},
        ],
        "red_flags": [],
    },
    "legal": {
        "pending_litigation": [],
        "regulatory_compliance": {
            "osha": "Compliant — third-party audited 2025-11",
            "iso": "ISO 9001 + ISO 27001 certified",
        },
        "red_flags": [],
    },
    "technical": {
        "tech_stack": {
            "backend": "Go 1.22 + Rust control plane",
            "database": "PostgreSQL 16, Redis 7",
            "infrastructure": "Kubernetes on GCP, multi-region",
            "frontend": "React 19",
        },
        "security": {
            "last_penetration_test": "Completed 2026-02 by NCC Group — no critical findings",
            "encryption_at_rest": "AES-256 across all stores",
            "soc2": "SOC2 Type II certified",
            "incident_history": "No security breaches to date",
        },
        "red_flags": [],
    },
    "market": {
        "tam_claim": "$48B warehouse automation market, growing 23% YoY",
        "competitors": [
            {"name": "Locus Robotics", "funding_raised": "$430M", "threat_level": "medium"},
            {"name": "6 River Systems", "funding_raised": "$46M", "threat_level": "low"},
        ],
        "red_flags": [],
    },
    "document_text": "Helios Robotics ARR is $18M current run rate, growing 140% YoY. "
                     "Warehouse automation sector growth is 23% YoY. Strong tailwinds.",
}

# ─────────────────────────────────────────────────────────────────────────────
# COMPANY B — "Auria Telehealth" : MIXED / borderline. Should be CONDITIONAL/PASS.
#   Decent ARR + margin, but: 58% concentration in one health system, FDA/telehealth
#   licensing gap (healthcare-unlicensed branch), 11-mo runway, heavy FDA-cleared
#   competitor. Tests the healthcare regulatory path + concentration scenario engine.
# ─────────────────────────────────────────────────────────────────────────────
auria = {
    "company": {
        "name": "Auria Telehealth",
        "industry": "Digital Health / Telehealth + Diagnostics AI",
        "stage": "Series A",
        "raise_amount": "$12,000,000",
        "post_money_valuation": "$55,000,000",
    },
    "financials": {
        "arr_raw": 6500000,
        "monthly_burn_usd": 700000,
        "runway_months": 11,
        "gross_margin_pct": 64,
        "customer_revenue_breakdown": [
            {"customer": "Ascension Health System", "revenue_pct": 58,
             "note": "Master services agreement renewal in 3 months after close"},
            {"customer": "Regional clinics (14)", "revenue_pct": 30},
            {"customer": "Direct-to-consumer", "revenue_pct": 12},
        ],
        "red_flags": ["58% revenue concentration in Ascension; MSA renewal pending"],
    },
    "legal": {
        "pending_litigation": [],
        "regulatory_compliance": {
            "fda": "Diagnostic AI module may require FDA 510(k) clearance; clearance not yet obtained",
            "hipaa": "HIPAA compliant — BAA in place with all covered entities",
            "telehealth": "Operating telehealth in 18 states; may require licensing in 6 additional states",
        },
        "red_flags": ["FDA 510(k) clearance pending for diagnostic module"],
    },
    "technical": {
        "tech_stack": {
            "backend": "Python 3.11 + FastAPI",
            "database": "PostgreSQL 15",
            "infrastructure": "AWS ECS, HIPAA-eligible services",
        },
        "security": {
            "last_penetration_test": "Completed 2025-09",
            "encryption_at_rest": "AES-256",
            "phi_storage": "Encrypted; field-level encryption on PHI",
            "soc2": "SOC2 Type I (Type II in progress)",
        },
        "red_flags": [],
    },
    "market": {
        "tam_claim": "$30B telehealth + diagnostics market, growing 18% YoY",
        "competitors": [
            {"name": "Viz.ai", "funding_raised": "$250M", "threat_level": "high",
             "note": "FDA-cleared diagnostic AI, bundling free with hospital EMR deals"},
            {"name": "Aidoc", "funding_raised": "$250M", "threat_level": "high"},
        ],
        "red_flags": ["FDA-cleared competitors bundling free diagnostics"],
    },
    "document_text": "Auria ARR is $6.5M current. Telehealth diagnostics market growing 18% YoY.",
}

# ─────────────────────────────────────────────────────────────────────────────
# COMPANY C — "QuantumLedger Pay" : DISASTER + tricky contradictions.
#   Sub-3-mo runway, plaintext SSNs, EOL stack, $9M lawsuit vs $8M raise, unlicensed
#   money transmitter, declining market, AND a planted cross-section ARR contradiction
#   ($4M in overview vs $11M in financials, same 'current' timeframe) + 200%/-12%.
#   Should be PASS via red-flag override, with contradictions surfaced.
# ─────────────────────────────────────────────────────────────────────────────
quantum = {
    "company": {
        "name": "QuantumLedger Pay",
        "industry": "Crypto Payments / Stablecoin Rails",
        "stage": "Seed",
        "raise_amount": "$8,000,000",
        "post_money_valuation": "$32,000,000",
    },
    "financials": {
        "arr_raw": 11000000,
        "monthly_burn_usd": 900000,
        "runway_months": 2,
        "gross_margin_pct": 31,
        "customer_revenue_breakdown": [
            {"customer": "CryptoMart Exchange", "revenue_pct": 81,
             "note": "Contract expires Sept 30, 2026, 3 months after close; termination-for-convenience clause"},
            {"customer": "Misc merchants", "revenue_pct": 19},
        ],
        "red_flags": ["81% concentration in CryptoMart, contract expires in 3 months"],
    },
    "legal": {
        "pending_litigation": [
            {"case": "Circle Internet Financial v. QuantumLedger (Case No. 1:2026cv00921)",
             "type": "Patent Infringement",
             "potential_damages_usd": 9000000,
             "status": "Discovery"},
        ],
        "regulatory_compliance": {
            "money_transmitter_licenses": "Unlicensed money transmitter in all 50 states; lacks money transmission licenses",
            "cfpb": "Non-compliant with CFPB rules; no independent audit conducted",
            "sec": "SEC investigation opened 2025 into prior token sale; founder accused of misrepresenting reserves",
        },
        "red_flags": ["$9M Circle lawsuit = 112% of raise", "Unlicensed in all 50 states", "SEC investigation"],
    },
    "technical": {
        "tech_stack": {
            "backend": "Node.js 14 (EOL)",
            "database": "MongoDB 4.2 (EOL)",
        },
        "security": {
            "last_penetration_test": "Never conducted; vulnerabilities remain unpatched",
            "pii_storage": "Customer SSNs and private keys stored in plaintext, unencrypted",
            "encryption_at_rest": "None",
            "incident_history": "Undisclosed breach 2025: leaked DB connection string on public GitHub, not reported to regulators",
        },
        "red_flags": ["Plaintext SSNs + private keys", "EOL stack", "Undisclosed breach"],
    },
    "market": {
        "tam_claim": "$2T stablecoin market by 2030 (company projection)",
        "competitors": [
            {"name": "Circle", "valuation": "$9B", "threat_level": "existential"},
            {"name": "Stripe Crypto", "threat_level": "high", "note": "bundling free stablecoin rails"},
        ],
        "red_flags": ["Crypto payments VC funding down 67% YoY", "Sector declining"],
    },
    "document_text": (
        "## Overview\nQuantumLedger Pay current ARR is $4,000,000 with 200% YoY growth.\n"
        "## Financials\nCurrent ARR run rate is $11,000,000.\n"
        "## Market\nStablecoin payments sector is declining -12% YoY amid regulatory crackdown."
    ),
}


def grade(calc, name, expected_verdict, checks):
    """Print key engine output line-by-line and grade /100 against `checks`."""
    print("=" * 78)
    print(f"COMPANY: {calc['company_name']}  ({calc['industry']}, {calc['stage']})")
    print(f"  raise={calc['raise_amount']}  valuation={calc['valuation']}")
    print("-" * 78)
    print(f"  Financial risk : {calc['fin_score']}  -> {calc['fin_rec']}")
    print(f"  Legal risk     : {calc['leg_score']}  -> {calc['leg_rec']}")
    print(f"  Technical risk : {calc['tech_score']}  -> {calc['tech_rec']}")
    print(f"  Market risk    : {calc['mkt_score']}  -> {calc['mkt_rec']}")
    print(f"  WEIGHTED       : {calc['weighted_score']}")
    print(f"  VERDICT        : {calc['verdict']}   (expected ~{expected_verdict})")
    print(f"  Coverage       : {calc['coverage_score']}%   Missing: {calc['missing_gaps']}")
    print(f"  Confidence     : {calc['verdict_confidence']:.0f}%   Evidence Q: {calc['evidence_quality_score']:.0f}")
    print(f"  Deal readiness : {calc['deal_readiness_score']:.0f} ({calc['deal_readiness_status']})")
    print(f"  Override reasons: {calc['override_reasons']}")
    print(f"  Contradictions : {[c['message'] for c in calc['contradictions']]}")
    print(f"  Warnings       : {calc['validation_warnings']}")
    if calc.get("scenario"):
        s = calc["scenario"]
        print(f"  Scenario       : if {s['client_name']} ({s['concentration_pct']:.0f}%) churns -> "
              f"ARR ${s['new_arr']:,.0f}, runway {s['new_runway']:.1f}mo, val ${s['new_valuation']:,.0f}")
    print(f"  CEO Qs   : {calc['questions']['ceo']}")
    print(f"  CTO Qs   : {calc['questions']['cto']}")
    print(f"  Legal Qs : {calc['questions']['legal']}")
    print("-" * 78)
    score = 0
    for label, passed, weight in checks(calc):
        mark = "PASS" if passed else "FAIL"
        if passed:
            score += weight
        print(f"  [{mark}] (+{weight if passed else 0}/{weight}) {label}")
    print(f"  >>> GRADE: {score}/100")
    print()
    return score


def checks_helios(c):
    return [
        ("Verdict is INVEST (clean strong deal)", c["verdict"] == "INVEST", 30),
        ("Weighted score low (<4.0)", c["weighted_score"] is not None and c["weighted_score"] < 4.0, 15),
        ("No override reasons (nothing fatal)", len(c["override_reasons"]) == 0, 15),
        ("Top customer concentration <30% -> no scenario", c["scenario"] is None, 10),
        ("Coverage high (>=70%)", c["coverage_score"] >= 70, 10),
        ("No contradictions", len(c["contradictions"]) == 0, 10),
        ("Each partner rec INVEST", all(c[k] == "INVEST" for k in ["fin_rec", "leg_rec", "tech_rec", "mkt_rec"]), 10),
    ]


def checks_auria(c):
    qs = " ".join(c["questions"]["ceo"] + c["questions"]["legal"]).lower()
    return [
        ("Verdict CONDITIONAL or PASS (not naive INVEST)", c["verdict"] in ("CONDITIONAL", "PASS"), 25),
        ("Healthcare licensing flagged -> legal override OR leg_score raised",
         "license" in str(c["override_reasons"]).lower() or (c["leg_score"] or 0) >= 4.0, 15),
        ("58% concentration triggers scenario analysis", c["scenario"] is not None, 15),
        ("Scenario churn cuts ARR materially",
         c["scenario"] is not None and c["scenario"]["new_arr"] < 6500000, 10),
        ("Runway <12mo surfaced in CEO questions", "runway" in qs, 10),
        ("Concentration surfaced in CEO questions", "58%" in qs or "concentration" in qs, 10),
        ("Heavy FDA-cleared competitor raises market risk", (c["mkt_score"] or 0) >= 4.0, 15),
    ]


def checks_quantum(c):
    ov = " ".join(c["override_reasons"]).lower()
    return [
        ("Verdict is PASS (reject)", c["verdict"] == "PASS", 20),
        ("Weighted score floored high (>=7.5 via override)", c["weighted_score"] is not None and c["weighted_score"] >= 7.5, 10),
        ("Override: lawsuit > 50% of raise", "lawsuit" in ov and "raise" in ov, 10),
        ("Override: plaintext PII", "plaintext" in ov or "unencrypted" in ov, 10),
        ("Override: unlicensed", "license" in ov, 10),
        ("Override: critical runway", "runway" in ov, 10),
        ("Override: SEC/misrepresentation", "regulatory" in ov or "misrepresent" in ov, 5),
        ("Override: undisclosed breach", "breach" in ov, 5),
        ("Cross-section ARR contradiction detected ($4M vs $11M current)", len(c["contradictions"]) >= 1, 10),
        ("200% vs -12% sector validation warning", any("200%" in w or "growth" in w.lower() for w in c["validation_warnings"]), 10),
    ]


if __name__ == "__main__":
    total = 0
    total += grade(run_diligence_calculations(helios), "Helios", "INVEST", checks_helios)
    total += grade(run_diligence_calculations(auria), "Auria", "CONDITIONAL/PASS", checks_auria)
    total += grade(run_diligence_calculations(quantum), "QuantumLedger", "PASS", checks_quantum)
    print("=" * 78)
    print(f"AGGREGATE ENGINE SCORE: {total}/300  ({total/3:.0f}/100 avg)")
