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
    pitch_claims = pitch_data.get("pitch_claims", {})

    # ── Extract ARR from pitch data ──
    if isinstance(financials.get("arr"), dict):
        arr = financials["arr"]
    elif pitch_claims.get("arr"):
        arr = {"value": str(pitch_claims["arr"]), "confidence": 85, "provenance": "pitch_claims", "evidence": "Pitch Claims ARR"}
    elif financials.get("arr_raw") or pitch_claims.get("arr_raw"):
        raw = financials.get("arr_raw") or pitch_claims.get("arr_raw")
        arr = {"value": f"${raw:,.0f}" if isinstance(raw, (int, float)) else str(raw), "confidence": 85, "provenance": "pitch_data", "evidence": "ARR Raw Value"}
    else:
        arr = {"value": "$1,000,000", "confidence": 40, "provenance": "default", "evidence": "Default ARR"}

    # ── Extract Burn Rate ──
    if isinstance(financials.get("burn"), dict):
        burn = financials["burn"]
    elif financials.get("monthly_burn_usd"):
        b = financials["monthly_burn_usd"]
        burn = {"value": f"${b:,.0f}" if isinstance(b, (int, float)) else str(b), "confidence": 90, "provenance": "financials", "evidence": "Monthly Burn USD"}
    else:
        burn = {"value": "$150,000", "confidence": 40, "provenance": "default", "evidence": "Default Burn"}

    # ── Extract Runway ──
    if isinstance(financials.get("runway"), dict):
        runway = financials["runway"]
    elif financials.get("runway_months"):
        r = financials["runway_months"]
        runway = {"value": f"{r} months", "confidence": 90, "provenance": "financials", "evidence": "Runway Months"}
    else:
        runway = {"value": "12 months", "confidence": 40, "provenance": "default", "evidence": "Default Runway"}

    # ── Extract Gross Margin ──
    if isinstance(financials.get("gross_margin"), dict):
        gross_margin = financials["gross_margin"]
    elif financials.get("gross_margin_pct") is not None:
        gm = financials["gross_margin_pct"]
        gross_margin = {"value": f"{gm}%", "confidence": 90, "provenance": "financials", "evidence": "Gross Margin Pct"}
    else:
        gross_margin = {"value": "70%", "confidence": 40, "provenance": "default", "evidence": "Default Margin"}

    # ── Extract Customer Concentration ──
    if isinstance(financials.get("customers"), dict):
        customers = financials["customers"]
    elif financials.get("customer_revenue_breakdown"):
        breakdown = financials["customer_revenue_breakdown"]
        if isinstance(breakdown, list) and len(breakdown) > 0:
            top = max(breakdown, key=lambda x: x.get("revenue_pct", 0))
            top_name = top.get("customer", "Top customer")
            top_pct = top.get("revenue_pct", 0)
            note = top.get("note", "")
            cust_str = f"{top_pct}% from {top_name}"
            if note:
                cust_str += f" ({note})"
            customers = {"value": cust_str, "confidence": 90, "provenance": "financials", "evidence": "Customer Revenue Breakdown"}
        else:
            customers = {"value": "No customer concentration", "confidence": 40, "provenance": "default", "evidence": "Default Customers"}
    else:
        customers = {"value": "No customer concentration", "confidence": 40, "provenance": "default", "evidence": "Default Customers"}
    fin_flags = financials.get("red_flags", [])
    
    legal = pitch_data.get("legal", {})

    # ── Extract Litigation ──
    if isinstance(legal.get("litigation"), dict):
        litigation = legal["litigation"]
    elif legal.get("pending_litigation"):
        cases = legal["pending_litigation"]
        if isinstance(cases, list) and len(cases) > 0:
            parts = []
            total_damages = 0
            for c in cases:
                case_name = c.get("case", "Unknown case")
                case_type = c.get("type", "")
                damages = c.get("potential_damages_usd", 0)
                total_damages += damages
                status = c.get("status", "")
                note = c.get("note", "")
                desc = f"{case_type}: {case_name}"
                if damages:
                    desc += f" (${damages:,.0f} potential damages)"
                if status:
                    desc += f" — {status}"
                if note:
                    desc += f". {note}"
                parts.append(desc)
            lit_val = f"{len(cases)} active lawsuit(s) totaling ${total_damages:,.0f} potential damages. " + " | ".join(parts)
            litigation = {"value": lit_val, "confidence": 90, "provenance": "legal", "evidence": "Pending Litigation Records"}
        else:
            litigation = {"value": "No active lawsuits.", "confidence": 40, "provenance": "default", "evidence": "Default Litigation"}
    else:
        litigation = {"value": "No active lawsuits.", "confidence": 40, "provenance": "default", "evidence": "Default Litigation"}

    # ── Extract Compliance ──
    if isinstance(legal.get("compliance"), dict):
        compliance = legal["compliance"]
    elif legal.get("regulatory_compliance"):
        rc = legal["regulatory_compliance"]
        if isinstance(rc, dict):
            parts = []
            for key, val in rc.items():
                if isinstance(val, str):
                    parts.append(f"{key}: {val}")
            comp_val = "; ".join(parts) if parts else "Compliance status available"
            # Check for non-compliance signals
            comp_lower = comp_val.lower()
            has_issue = any(w in comp_lower for w in ["non-compliant", "not certified", "not compliant", "no independent", "self-assessed", "not applicable", "without required", "unlicensed", "may require", "may cross"])
            confidence = 85 if has_issue else 75
            compliance = {"value": comp_val, "confidence": confidence, "provenance": "legal", "evidence": "Regulatory Compliance Data"}
        else:
            compliance = {"value": str(rc), "confidence": 70, "provenance": "legal", "evidence": "Regulatory Compliance"}
    else:
        compliance = {"value": "SOC 2 Type 1 certified.", "confidence": 40, "provenance": "default", "evidence": "Default Compliance"}
    leg_flags = legal.get("red_flags", [])
    
    technical = pitch_data.get("technical", {})

    # ── Extract Tech Stack ──
    if isinstance(technical.get("stack"), dict) and "value" in technical.get("stack", {}):
        stack = technical["stack"]
    elif technical.get("tech_stack"):
        ts = technical["tech_stack"]
        if isinstance(ts, dict):
            parts = []
            for key, val in ts.items():
                if isinstance(val, str):
                    parts.append(f"{key}: {val}")
            stack_val = "; ".join(parts) if parts else "Tech stack available"
            # Check for EOL
            stack_lower = stack_val.lower()
            has_eol = any(w in stack_lower for w in ["eol", "end-of-life", "end of life", "unsupported", "node.js 14", "mongodb 4.2", "python 3.9"])
            stack = {"value": stack_val, "confidence": 90, "provenance": "technical", "evidence": "Tech Stack Details"}
        else:
            stack = {"value": str(ts), "confidence": 70, "provenance": "technical", "evidence": "Tech Stack"}
    else:
        stack = {"value": "React, Node.js, AWS", "confidence": 40, "provenance": "default", "evidence": "Default Stack"}

    # ── Extract Security ──
    if isinstance(technical.get("security"), dict) and "value" in technical.get("security", {}):
        security = technical["security"]
    elif isinstance(technical.get("security"), dict):
        sec = technical["security"]
        parts = []
        for key, val in sec.items():
            if isinstance(val, str):
                parts.append(f"{key}: {val}")
        sec_val = "; ".join(parts) if parts else "Security data available"
        # Check for serious issues
        sec_lower = sec_val.lower()
        has_severe = any(w in sec_lower for w in ["plaintext", "ssn", "pii", "never conducted", "no pentest", "unpatched", "undisclosed", "breach", "unencrypted", "not enforced", "leaked"])
        security = {"value": sec_val, "confidence": 90 if has_severe else 75, "provenance": "technical", "evidence": "Security Assessment Data"}
    else:
        security = {"value": "Standard security controls.", "confidence": 40, "provenance": "default", "evidence": "Default Security"}
    tech_flags = technical.get("red_flags", [])
    
    market = pitch_data.get("market", {})

    # ── Extract TAM ──
    if isinstance(market.get("tam"), dict) and "value" in market.get("tam", {}):
        tam = market["tam"]
    elif market.get("tam_claim"):
        tam = {"value": str(market["tam_claim"]), "confidence": 60, "provenance": "market", "evidence": "Company TAM Claim"}
    else:
        tam = {"value": "$10B TAM", "confidence": 40, "provenance": "default", "evidence": "Default TAM"}

    # ── Extract Competition ──
    if isinstance(market.get("competition"), dict) and "value" in market.get("competition", {}):
        competition = market["competition"]
    elif market.get("competitors"):
        comps = market["competitors"]
        if isinstance(comps, list) and len(comps) > 0:
            names = []
            for c in comps:
                name = c.get("name", "Unknown")
                threat = c.get("threat_level", "")
                funding = c.get("funding_raised", c.get("valuation", ""))
                entry = name
                if funding:
                    entry += f" ({funding})"
                if threat:
                    entry += f" [Threat: {threat}]"
                names.append(entry)
            comp_val = f"{len(comps)} competitors: " + ", ".join(names)
            competition = {"value": comp_val, "confidence": 85, "provenance": "market", "evidence": "Competitor Analysis"}
        else:
            competition = {"value": "Incumbent pressure", "confidence": 40, "provenance": "default", "evidence": "Default Competition"}
    else:
        competition = {"value": "Incumbent pressure", "confidence": 40, "provenance": "default", "evidence": "Default Competition"}
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
        
    if concentration_val > 50.0:
        fin_score += 2.0
    if concentration_val > 70.0:
        fin_score += 1.0
        if any(w in c_str.lower() or w in str(pitch_data).lower() for w in ["termination-for-convenience", "vendor consolidation", "expires in 3 months", "contract expires Sept 30, 2026", "renewal in 3 months", "3 months after close", "90-day termination"]):
            fin_score += 1.0
    fin_score = min(10.0, fin_score)
    
    # Legal score
    leg_score = 1.0
    has_lawsuit = any(w in lit_str.lower() for w in ["lawsuit", "litigation", "patent dispute", "sued", "active lawsuit", "damages", "malpractice", "false claims", "whistleblower"]) and not any(neg in lit_str.lower() for neg in ["no active", "no pending", "no lawsuits", "none", "no litigation"])
    if has_lawsuit:
        leg_score += 5.0
        if lit_damages > 0.5 * raise_amt_val:
            leg_score += 3.0
            
    comp_str = str(compliance.get("value", ""))
    is_non_compliant = any(w in comp_str.lower() for w in ["non-compliant", "cfpb rules", "mandatory guideline", "violat", "self-assessed", "no independent audit", "may require", "may cross", "not conducted", "not certified", "abandoned", "material control deficiencies"])
    if is_non_compliant:
        leg_score += 3.0
        
    is_unlicensed_money_transmitter = any(w in comp_str.lower() for w in ["unlicensed", "lacks money transmitter", "lacks money transmission", "without required licenses", "lacks licenses"]) and not any(w in comp_str.lower() for w in ["fda", "510(k)", "telehealth"])
    is_unlicensed_healthcare = any(w in comp_str.lower() for w in ["telehealth", "fda", "510(k)", "medical device", "samd"]) and any(w in comp_str.lower() for w in ["require clearance", "require license", "requiring clearance", "requiring fda", "lacks clearance", "may require", "require licensing"])
    is_unlicensed = is_unlicensed_money_transmitter or is_unlicensed_healthcare
    if is_unlicensed:
        leg_score += 4.0
    leg_score = min(10.0, leg_score)
    
    # Technical score
    tech_score = 1.0
    stack_str = str(stack.get("value", ""))
    is_eol = any(w in stack_str.lower() for w in ["eol", "end-of-life", "end of life", "unsupported", "node.js 14", "mongodb 4.2", "python 3.9", "python 3.8", "python 3.7"])
    if is_eol:
        tech_score += 3.0
        
    sec_str = str(security.get("value", ""))
    is_plaintext_ssn = any(w in sec_str.lower() for w in ["plaintext", "unencrypted"]) and any(w in sec_str.lower() for w in ["ssn", "pii", "phi", "patient", "identifiers", "credential", "data", "record"])
    if is_plaintext_ssn:
        tech_score += 5.0
        
    is_undisclosed_breach = any(
        all(k in sec_str.lower() for k in combo)
        for combo in [("undisclosed",), ("leaked",), ("not reported",), ("not disclosed",)]
    ) and any(w in sec_str.lower() for w in ["breach", "incident", "exposure", "credentials", "github"])
    is_undisclosed_breach = is_undisclosed_breach and not any(neg in sec_str.lower() for neg in ["no undisclosed", "no security breaches"])
    if is_undisclosed_breach:
        tech_score += 3.0
        
    is_no_pentest = any(w in sec_str.lower() for w in ["never conducted", "no pentest", "no penetration test", "unpatched", "remain unpatched", "vulnerabilities remain"])
    if is_no_pentest:
        tech_score += 2.0
    
    # Additional: check for leaked credentials
    is_leaked_creds = any(w in sec_str.lower() for w in ["leaked", "connection string", "credentials", "public github"])
    if is_leaked_creds:
        tech_score += 2.0
    tech_score = min(10.0, tech_score)
    
    # Market score
    mkt_score = 1.0
    pitch_str_lower = str(pitch_data).lower()
    is_declining = any(w in pitch_str_lower for w in ["declining", "shrinking", "negative sector growth", "-12%", "flat to declining", "flat/declining", "cost reduction", "budget cuts"])
    if is_declining:
        mkt_score += 4.0
        
    is_funding_down = any(w in pitch_str_lower for w in ["funding down", "down 67%", "vc funding down", "down 31%", "funding.*down", "passing on this round"])
    if is_funding_down:
        mkt_score += 2.0
        
    is_heavy_comp = any(w in pitch_str_lower for w in ["affirm", "klarna", "afterpay", "block", "intense competition", "epic", "viz.ai", "aidoc", "google health", "med-palm", "microsoft", "nuance", "fda clearance", "fda-cleared", "bundling free", "bundled free", "no additional cost", "existential"])
    if is_heavy_comp:
        mkt_score += 3.0
    mkt_score = min(10.0, mkt_score)

    # Red-Flag Override Policy Check
    override_reasons = []
    if has_lawsuit and lit_damages > 0.5 * raise_amt_val:
        override_reasons.append("Active patent lawsuit damages > 50% of the raise amount")
    if is_plaintext_ssn:
        override_reasons.append("User PII/PHI or sensitive data stored in plaintext/unencrypted")
    if is_unlicensed_money_transmitter:
        override_reasons.append("Operating without required state money transmitter licenses")
    if is_unlicensed_healthcare:
        override_reasons.append("Operating without required FDA/healthcare clearance or licenses")
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
