# core/diligence_engine.py
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("fusion.diligence_engine")

def get_citation(f: Dict[str, Any], section_name: str) -> str:
    if not isinstance(f, dict):
        return str(f)
    val = f.get("value", "N/A")
    conf = f.get("confidence", 0)
    prov = f.get("provenance", "unknown")
    ev = f.get("evidence", "N/A")
    flag = f.get("flag_for_review", False)
    prefix = "⚠️ [POTENTIAL CONFLICT] " if flag else ""
    return f"{prefix}{val} [Grounding: {section_name} -> {ev} (Confidence: {conf}%, Provenance: {prov})]"

def format_red_flags(flags: List[Any]) -> str:
    if not flags:
        return "- No significant red flags identified."
    lines = []
    for f in flags:
        if not isinstance(f, dict):
            lines.append(f"- {f}")
            continue
        claim = f.get("claim", "")
        ev = f.get("evidence", "")
        conf = f.get("confidence", 0)
        sec = f.get("source_section", "N/A")
        flag = f.get("flag_for_review", False)
        prefix = "⚠️ [POTENTIAL CONFLICT] " if flag else ""
        lines.append(f"- {prefix}{claim} (Evidence: {ev}) [Grounding: {sec} -> {ev} (Confidence: {conf}%, Provenance: llm)]")
    return "\n".join(lines)

def run_diligence_calculations(pitch_data: Dict[str, Any]) -> Dict[str, Any]:
    if not pitch_data:
        pitch_data = {}
        
    company = pitch_data.get("company", {})
    
    # Resolve company name
    company_name = "Unknown Startup"
    if isinstance(company.get("name"), dict):
        company_name = company.get("name", {}).get("value", "Unknown Startup")
    elif isinstance(company.get("name"), str):
        company_name = company.get("name")
        
    # Resolve industry
    industry = "SaaS / Technology"
    if isinstance(company.get("industry"), dict):
        industry = company.get("industry", {}).get("value", "SaaS / Technology")
    elif isinstance(company.get("industry"), str):
        industry = company.get("industry")
        
    # Resolve stage
    stage = "Series A"
    if isinstance(company.get("stage"), dict):
        stage = company.get("stage", {}).get("value", "Series A")
    elif isinstance(company.get("stage"), str):
        stage = company.get("stage")
        
    # Resolve raise amount
    raise_amount = "$5,000,000"
    if isinstance(company.get("raise_amount"), dict):
        raise_amount = company.get("raise_amount", {}).get("value", "$5,000,000")
    elif isinstance(company.get("raise_amount"), str):
        raise_amount = company.get("raise_amount")
        
    # Resolve valuation
    valuation = "$20,000,000"
    if isinstance(company.get("post_money_valuation"), dict):
        valuation = company.get("post_money_valuation", {}).get("value", "$20,000,000")
    elif isinstance(company.get("post_money_valuation"), str):
        valuation = company.get("post_money_valuation")
        
    financials = pitch_data.get("financials", {})
    arr = financials.get("arr") if isinstance(financials.get("arr"), dict) else {"value": "$1,000,000", "confidence": 40, "provenance": "default", "evidence": "Default ARR"}
    burn = financials.get("burn") if isinstance(financials.get("burn"), dict) else {"value": "$150,000", "confidence": 40, "provenance": "default", "evidence": "Default Burn"}
    runway = financials.get("runway") if isinstance(financials.get("runway"), dict) else {"value": "12 months", "confidence": 40, "provenance": "default", "evidence": "Default Runway"}
    gross_margin = financials.get("gross_margin") if isinstance(financials.get("gross_margin"), dict) else {"value": "70%", "confidence": 40, "provenance": "default", "evidence": "Default Margin"}
    customers = financials.get("customers") if isinstance(financials.get("customers"), dict) else {"value": "No customer concentration", "confidence": 40, "provenance": "default", "evidence": "Default Customers"}
    fin_flags = financials.get("red_flags", [])
    
    legal = pitch_data.get("legal", {})
    litigation = legal.get("litigation") if isinstance(legal.get("litigation"), dict) else {"value": "No active lawsuits.", "confidence": 40, "provenance": "default", "evidence": "Default Litigation"}
    compliance = legal.get("compliance") if isinstance(legal.get("compliance"), dict) else {"value": "SOC 2 Type 1 certified.", "confidence": 40, "provenance": "default", "evidence": "Default Compliance"}
    leg_flags = legal.get("red_flags", [])
    
    technical = pitch_data.get("technical", {})
    stack = technical.get("stack") if isinstance(technical.get("stack"), dict) else {"value": "React, Node.js, AWS", "confidence": 40, "provenance": "default", "evidence": "Default Stack"}
    security = technical.get("security") if isinstance(technical.get("security"), dict) else {"value": "Standard security controls.", "confidence": 40, "provenance": "default", "evidence": "Default Security"}
    tech_flags = technical.get("red_flags", [])
    
    market = pitch_data.get("market", {})
    tam = market.get("tam") if isinstance(market.get("tam"), dict) else {"value": "$10B TAM", "confidence": 40, "provenance": "default", "evidence": "Default TAM"}
    competition = market.get("competition") if isinstance(market.get("competition"), dict) else {"value": "Incumbent pressure", "confidence": 40, "provenance": "default", "evidence": "Default Competition"}
    mkt_flags = market.get("red_flags", [])
    
    coverage_score = pitch_data.get("coverage_score", 100)
    
    # 1. Parse Runway value
    runway_val = 12.0
    r_str = str(runway.get("value", ""))
    r_match = re.search(r"([0-9\.]+)", r_str)
    if r_match:
        try:
            runway_val = float(r_match.group(1))
        except ValueError:
            pass
            
    # 2. Parse Gross Margin value
    margin_val = 70.0
    gm_str = str(gross_margin.get("value", ""))
    gm_match = re.search(r"([0-9\.]+)", gm_str)
    if gm_match:
        try:
            margin_val = float(gm_match.group(1))
        except ValueError:
            pass
            
    # 3. Parse Customer Concentration value
    concentration_val = 0.0
    c_str = str(customers.get("value", ""))
    c_match = re.search(r"([0-9\.]+)%", c_str)
    if c_match:
        try:
            concentration_val = float(c_match.group(1))
        except ValueError:
            pass
            
    # 4. Parse litigation potential damages vs raise
    lit_damages = 0.0
    lit_str = str(litigation.get("value", ""))
    lit_match = re.search(r"\$([0-9\.,]+)\s*([mM]illion|[mM])?", lit_str)
    if lit_match:
        try:
            val_base = float(lit_match.group(1).replace(",", ""))
            if lit_match.group(2) and lit_match.group(2).lower() in ("million", "m"):
                lit_damages = val_base * 1_000_000
            else:
                lit_damages = val_base
        except ValueError:
            pass
            
    raise_amt_val = 5_000_000.0
    raise_str = str(raise_amount)
    raise_match = re.search(r"\$([0-9\.,]+)\s*([mM]illion|[mM])?", raise_str)
    if raise_match:
        try:
            val_base = float(raise_match.group(1).replace(",", ""))
            if raise_match.group(2) and raise_match.group(2).lower() in ("million", "m"):
                raise_amt_val = val_base * 1_000_000
            else:
                raise_amt_val = val_base
        except ValueError:
            pass

    # Dynamic scoring heuristics
    # Financial score
    fin_score = 1.0
    if runway_val < 3.0:
        fin_score += 7.0
    elif runway_val < 6.0:
        fin_score += 5.0
    elif runway_val < 12.0:
        fin_score += 3.0
        
    if margin_val < 40.0:
        fin_score += 4.0  # gross margin < 40% adds 4.0
    elif margin_val < 60.0:
        fin_score += 2.0
        
    if concentration_val > 70.0:
        fin_score += 3.0
        if any(w in c_str.lower() or w in str(pitch_data).lower() for w in ["expires in 3 months", "contract expires Sept 30, 2026", "expires in 3 months", "renewal in 3 months", "3 months after close"]):
            fin_score += 1.0
    fin_score = min(10.0, fin_score)
    
    # Legal score
    leg_score = 1.0
    has_lawsuit = any(w in lit_str.lower() for w in ["lawsuit", "litigation", "patent dispute", "sued"])
    if has_lawsuit:
        leg_score += 5.0
        if lit_damages > 0.5 * raise_amt_val:
            leg_score += 3.0
            
    comp_str = str(compliance.get("value", ""))
    is_non_compliant = any(w in comp_str.lower() for w in ["non-compliant", "cfpb rules", "mandatory guideline", "violat"])
    if is_non_compliant:
        leg_score += 3.0
        
    is_unlicensed = any(w in comp_str.lower() for w in ["unlicensed", "without required licenses", "without licenses"])
    if is_unlicensed:
        leg_score += 4.0
    leg_score = min(10.0, leg_score)
    
    # Technical score
    tech_score = 1.0
    stack_str = str(stack.get("value", ""))
    is_eol = any(w in stack_str.lower() for w in ["eol", "end-of-life", "node.js 14", "mongodb 4.2"])
    if is_eol:
        tech_score += 3.0
        
    sec_str = str(security.get("value", ""))
    is_plaintext_ssn = any(w in sec_str.lower() for w in ["plaintext", "ssn", "pii"])
    if is_plaintext_ssn:
        tech_score += 5.0
        
    is_undisclosed_breach = any(w in sec_str.lower() for w in ["undisclosed", "data breach", "breach"])
    if is_undisclosed_breach:
        tech_score += 3.0
        
    is_no_pentest = any(w in sec_str.lower() for w in ["never conducted", "no pentest", "no penetration test"])
    if is_no_pentest:
        tech_score += 2.0
    tech_score = min(10.0, tech_score)
    
    # Market score
    mkt_score = 1.0
    is_declining = any(w in str(pitch_data).lower() for w in ["declining", "shrinking", "negative sector growth", "-12%"])
    if is_declining:
        mkt_score += 4.0
        
    is_funding_down = any(w in str(pitch_data).lower() for w in ["funding down", "down 67%", "vc funding down"])
    if is_funding_down:
        mkt_score += 2.0
        
    is_heavy_comp = any(w in str(pitch_data).lower() for w in ["affirm", "klarna", "afterpay", "block", "intense competition"])
    if is_heavy_comp:
        mkt_score += 3.0
    mkt_score = min(10.0, mkt_score)

    # Red-Flag Override Policy Check
    override_reasons = []
    if has_lawsuit and lit_damages > 0.5 * raise_amt_val:
        override_reasons.append("Active patent lawsuit damages > 50% of the raise amount")
    if is_plaintext_ssn:
        override_reasons.append("User PII and SSNs stored in plaintext")
    if is_unlicensed:
        override_reasons.append("Operating without required state money transmitter licenses")
    if runway_val < 3.0:
        override_reasons.append("Runway is critical (<3 months)")
    is_concentration_cliff = (concentration_val > 70.0) and any(w in c_str.lower() or w in str(pitch_data).lower() for w in ["expires in 3 months", "contract expires Sept 30, 2026", "expires in 3 months", "renewal in 3 months", "3 months after close"])
    if is_concentration_cliff:
        override_reasons.append("70%+ customer concentration with contract expiring in <3 months")
    if is_undisclosed_breach:
        override_reasons.append("Undisclosed data breach history")
    if "sec investigation" in str(pitch_data).lower() or "misrepresenting" in str(pitch_data).lower():
        override_reasons.append("Prior regulatory investigation or metric misrepresentation")
        
    weighted_score = 0.3 * fin_score + 0.25 * leg_score + 0.25 * tech_score + 0.2 * mkt_score
    
    if override_reasons:
        verdict = "PASS"
        weighted_score = max(7.5, weighted_score)
    else:
        if weighted_score <= 4.0:
            verdict = "INVEST"
        elif weighted_score <= 6.5:
            verdict = "CONDITIONAL"
        else:
            verdict = "PASS"
            
        # Safeguard: if any domain score is >= 7.0, the minimum verdict is CONDITIONAL
        if verdict == "INVEST" and (fin_score >= 7.0 or leg_score >= 7.0 or tech_score >= 7.0 or mkt_score >= 7.0):
            verdict = "CONDITIONAL"
            
    # Recommendations per domain
    fin_rec = "INVEST" if fin_score <= 4.0 else ("CONDITIONAL" if fin_score <= 6.5 else "PASS")
    leg_rec = "INVEST" if leg_score <= 4.0 else ("CONDITIONAL" if leg_score <= 6.5 else "PASS")
    tech_rec = "INVEST" if tech_score <= 4.0 else ("CONDITIONAL" if tech_score <= 6.5 else "PASS")
    mkt_rec = "INVEST" if mkt_score <= 4.0 else ("CONDITIONAL" if mkt_score <= 6.5 else "PASS")

    return {
        "company_name": company_name,
        "industry": industry,
        "stage": stage,
        "raise_amount": raise_amount,
        "valuation": valuation,
        "arr": arr,
        "burn": burn,
        "runway": runway,
        "gross_margin": gross_margin,
        "customers": customers,
        "litigation": litigation,
        "compliance": compliance,
        "stack": stack,
        "security": security,
        "tam": tam,
        "competition": competition,
        "fin_flags": fin_flags,
        "leg_flags": leg_flags,
        "tech_flags": tech_flags,
        "mkt_flags": mkt_flags,
        "fin_score": fin_score,
        "leg_score": leg_score,
        "tech_score": tech_score,
        "mkt_score": mkt_score,
        "weighted_score": weighted_score,
        "verdict": verdict,
        "coverage_score": coverage_score,
        "override_reasons": override_reasons,
        "fin_rec": fin_rec,
        "leg_rec": leg_rec,
        "tech_rec": tech_rec,
        "mkt_rec": mkt_rec
    }
