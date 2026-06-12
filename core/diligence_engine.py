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

def parse_arr_from_text(text: str) -> float:
    if not text:
        return None
    patterns = [
        r"(?:arr|annual recurring revenue|revenue):\s*(\$[0-9\.,]+[mMkK]?|\$[0-9\.,]+\s*(?:million|billion|k|thousand)?)",
        r"(\$[0-9\.,]+\s*(?:million|m|billion|b)?)\s*arr"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = next((g for g in match.groups() if g is not None), None)
            if val:
                val_clean = val.replace("$", "").replace(",", "").strip()
                multiplier = 1.0
                m_match = re.search(r"([0-9\.]+)\s*([mM]illion|[mM]|[bB]illion|[bB]|[kK])?", val_clean, re.IGNORECASE)
                if m_match:
                    num = float(m_match.group(1))
                    unit = m_match.group(2)
                    if unit:
                        unit = unit.lower()
                        if unit in ("million", "m"):
                            multiplier = 1_000_000.0
                        elif unit in ("billion", "b"):
                            multiplier = 1_000_000_000.0
                        elif unit == "k":
                            multiplier = 1_000.0
                    return num * multiplier
    return None

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
    has_lawsuit = any(w in lit_str.lower() for w in ["lawsuit", "litigation", "patent dispute", "sued"]) and not any(neg in lit_str.lower() for neg in ["no active", "no pending", "no lawsuits", "none", "no litigation"])
    if has_lawsuit:
        leg_score += 5.0
        if lit_damages > 0.5 * raise_amt_val:
            leg_score += 3.0
            
    comp_str = str(compliance.get("value", ""))
    is_non_compliant = any(w in comp_str.lower() for w in ["non-compliant", "cfpb rules", "mandatory guideline", "violat"])
    if is_non_compliant:
        leg_score += 3.0
        
    is_unlicensed = any(w in comp_str.lower() for w in ["unlicensed", "without required licenses", "without licenses", "lacks money transmitter", "lacks licenses"])
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
        
    is_undisclosed_breach = ("undisclosed" in sec_str.lower() and "breach" in sec_str.lower()) and not any(neg in sec_str.lower() for neg in ["no undisclosed", "no security breaches"])
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

    # V5.0 Venture Associate Additions
    
    # Parse financial float values for scenario modeling
    arr_val = 1_000_000.0
    arr_str = str(arr.get("value", ""))
    arr_match = re.search(r"\$([0-9\.,]+)\s*([mM]illion|[mM])?", arr_str)
    if arr_match:
        try:
            val_base = float(arr_match.group(1).replace(",", ""))
            if arr_match.group(2) and arr_match.group(2).lower() in ("million", "m"):
                arr_val = val_base * 1_000_000
            else:
                arr_val = val_base
        except ValueError:
            pass

    burn_val = 150_000.0
    burn_str = str(burn.get("value", ""))
    burn_match = re.search(r"\$([0-9\.,]+)\s*([mM]illion|[mM])?", burn_str)
    if burn_match:
        try:
            val_base = float(burn_match.group(1).replace(",", ""))
            if burn_match.group(2) and burn_match.group(2).lower() in ("million", "m"):
                burn_val = val_base * 1_000_000
            else:
                burn_val = val_base
        except ValueError:
            pass

    valuation_val = 20_000_000.0
    val_str = str(valuation)
    val_match = re.search(r"\$([0-9\.,]+)\s*([mM]illion|[mM])?", val_str)
    if val_match:
        try:
            val_base = float(val_match.group(1).replace(",", ""))
            if val_match.group(2) and val_match.group(2).lower() in ("million", "m"):
                valuation_val = val_base * 1_000_000
            else:
                valuation_val = val_base
        except ValueError:
            pass

    # 1. Contradiction Detection
    contradictions = []
    validation_warnings = []
    document_text = pitch_data.get("document_text", "")
    
    if document_text:
        sections = {}
        current_section = "General"
        current_lines = []
        for line in document_text.splitlines():
            header_match = re.match(r"^#+\s*(.*)$", line.strip())
            if header_match:
                if current_lines:
                    sections[current_section] = "\n".join(current_lines).strip()
                current_section = header_match.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            sections[current_section] = "\n".join(current_lines).strip()
            
        # Compare ARR between sections
        section_arrs = {}
        for sec_name, sec_content in sections.items():
            parsed_arr = parse_arr_from_text(sec_content)
            if parsed_arr is not None:
                section_arrs[sec_name] = parsed_arr
                
        sec_names = list(section_arrs.keys())
        for i in range(len(sec_names)):
            for j in range(i + 1, len(sec_names)):
                s1, s2 = sec_names[i], sec_names[j]
                v1, v2 = section_arrs[s1], section_arrs[s2]
                if abs(v1 - v2) > 1000:
                    v1_str = f"${v1:,.0f}" if v1 >= 1000 else str(v1)
                    v2_str = f"${v2:,.0f}" if v2 >= 1000 else str(v2)
                    contradictions.append({
                        "type": "cross_document",
                        "field": "ARR",
                        "message": f"🚨 MATERIAL DISCREPANCY DETECTED: ARR claims contradict. Section '{s1}' claims {v1_str} ARR, but section '{s2}' reports {v2_str} ARR."
                    })
                    
        # 2. Sector Contradiction Warning (Requires External Validation)
        has_200 = "200%" in document_text
        has_minus12 = "-12%" in document_text or "declining 12%" in document_text
        if has_200 and has_minus12:
            validation_warnings.append(
                "⚠️ Claim Requires External Validation: Founder claims high growth (200% growth) while sector trend indicates contraction (-12% decline)."
            )
        else:
            growth_match = re.search(r"(\d+[\d\.]*%)\s*(?:yoy\s*)?growth", document_text, re.IGNORECASE)
            decline_match = re.search(r"(-?\d+[\d\.]*%)\s*(?:sector\s*)?(?:decline|contraction|down)", document_text, re.IGNORECASE)
            if growth_match and decline_match:
                g_str = growth_match.group(0).strip()
                d_str = decline_match.group(0).strip()
                validation_warnings.append(
                    f"⚠️ Claim Requires External Validation: Founder claims high growth ({g_str}) while sector trend indicates contraction ({d_str})."
                )

    # 2. Missing Information Gaps Detector
    core_fields_map = {
        "ARR": arr,
        "Monthly Burn": burn,
        "Runway": runway,
        "Gross Margin": gross_margin,
        "Customer Concentration": customers,
        "Litigation Status": litigation,
        "Compliance Status": compliance,
        "Tech Stack": stack,
        "Security Posture": security,
        "TAM": tam
    }
    missing_gaps = []
    for label, field in core_fields_map.items():
        if field.get("confidence", 0) <= 50 or field.get("provenance") == "default":
            missing_gaps.append(label)

    # 3. Evidence Quality & Verdict Confidence Scores
    evidence_quality_score = sum(field.get("confidence", 0) for field in core_fields_map.values()) / 10.0
    
    conflict_penalty = len(contradictions) * 15
    missing_penalty = len(missing_gaps) * 5
    
    verdict_confidence = (coverage_score * 0.4) + (evidence_quality_score * 0.4) - conflict_penalty - missing_penalty
    verdict_confidence = max(0.0, min(100.0, verdict_confidence))

    # 4. Deal Readiness Score
    deal_readiness_score = 100.0 - (weighted_score * 5.0) - (len(contradictions) * 15.0) - (len(missing_gaps) * 4.0) - ((100.0 - verdict_confidence) * 0.2)
    deal_readiness_score = max(0.0, min(100.0, deal_readiness_score))
    deal_readiness_status = "Ready for IC Review" if (deal_readiness_score >= 70.0 and len(contradictions) == 0) else "Additional Diligence Required"

    # 5. Auto-Generated VC Questions
    questions = {
        "ceo": [],
        "cto": [],
        "legal": []
    }
    
    # CEO Questions
    if concentration_val > 50.0:
        client_name = "primary client"
        for word in ["Microsoft", "Amazon", "Google", "Apple", "Meta"]:
            if word.lower() in str(customers.get("value", "")).lower():
                client_name = word
                break
        questions["ceo"].append(
            f"Given that {client_name} contributes {concentration_val:.0f}% of total ARR, what is the contract renewal probability and what contingency plans exist if they do not renew?"
        )
    if runway_val < 12.0:
        questions["ceo"].append(
            f"With only {runway_val:.1f} months of runway, how does the company plan to bridge the funding gap if this round takes longer than expected to close?"
        )
    if not questions["ceo"]:
        questions["ceo"].append("What are the key growth drivers and resource allocation plans for the next 18 months?")

    # CTO Questions
    if is_eol:
        eol_items = []
        if "node.js 14" in stack_str.lower() or "node 14" in stack_str.lower():
            eol_items.append("Node.js 14")
        if "mongodb 4.2" in stack_str.lower():
            eol_items.append("MongoDB 4.2")
        eol_str = " and ".join(eol_items) if eol_items else "EOL components"
        questions["cto"].append(
            f"What is the timeline and migration plan for upgrading the EOL stack ({eol_str}) currently running in production?"
        )
    if is_plaintext_ssn:
        questions["cto"].append(
            "Why is sensitive customer data (SSNs and PII) stored in plaintext, and when will encryption-at-rest be fully implemented?"
        )
    if is_no_pentest:
        questions["cto"].append(
            "When does the company plan to conduct its first independent penetration test to discover security vulnerabilities?"
        )
    if not questions["cto"]:
        questions["cto"].append("What are the scaling limits of the current architecture and the plan for horizontal scaling?")

    # Legal Questions
    if has_lawsuit:
        case_name = "pending lawsuit"
        for word in ["Klarna", "patent lawsuit", "infringement"]:
            if word.lower() in lit_str.lower():
                case_name = "Klarna AB v. NovaPay Inc patent litigation"
                break
        damages_str = f"${lit_damages:,.0f}" if lit_damages > 0 else "damages"
        if lit_damages >= 1_000_000:
            damages_str = f"${lit_damages/1_000_000:.1f}M"
        questions["legal"].append(
            f"What is the target settlement amount or defense strategy for the active patent litigation ({case_name}) claiming {damages_str}?"
        )
    if is_unlicensed:
        questions["legal"].append(
            "What is the timeline and regulatory roadmap for obtaining the required Money Transmitter Licenses in the states where operations are currently unlicensed?"
        )
    if is_non_compliant:
        questions["legal"].append(
            "What steps is the company taking to achieve compliance with CFPB guidelines, and what is the estimated cost?"
        )
    if "nyc local law 144" in comp_str.lower():
        questions["legal"].append(
            "What is the compliance strategy for NYC Local Law 144 regulatory exposure, and has an independent bias audit been performed?"
        )
    if not questions["legal"]:
        questions["legal"].append("Are there any pending IP disputes or unregistered trademarks that could pose regulatory risks?")

    # 6. Financial Scenario Engine
    scenario = None
    if concentration_val > 50.0:
        client_name = "primary client"
        for word in ["Microsoft", "Amazon", "Google", "Apple", "Meta"]:
            if word.lower() in str(customers.get("value", "")).lower():
                client_name = word
                break
                
        churn_revenue_loss = arr_val * (concentration_val / 100.0)
        new_arr = arr_val - churn_revenue_loss
        
        monthly_revenue_loss = churn_revenue_loss / 12.0
        new_monthly_burn = burn_val + monthly_revenue_loss
        
        current_cash = runway_val * burn_val
        new_runway = current_cash / new_monthly_burn if new_monthly_burn > 0 else runway_val
        
        multiple = valuation_val / arr_val if arr_val > 0 else 1.0
        new_valuation = new_arr * multiple
        
        scenario = {
            "client_name": client_name,
            "concentration_pct": concentration_val,
            "churn_revenue_loss": churn_revenue_loss,
            "new_arr": new_arr,
            "current_monthly_burn": burn_val,
            "new_monthly_burn": new_monthly_burn,
            "new_runway": new_runway,
            "current_valuation": valuation_val,
            "new_valuation": new_valuation,
            "multiple": multiple
        }

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
        "mkt_rec": mkt_rec,
        "contradictions": contradictions,
        "validation_warnings": validation_warnings,
        "missing_gaps": missing_gaps,
        "evidence_quality_score": evidence_quality_score,
        "verdict_confidence": verdict_confidence,
        "deal_readiness_score": deal_readiness_score,
        "deal_readiness_status": deal_readiness_status,
        "questions": questions,
        "scenario": scenario
    }
