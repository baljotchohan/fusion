# core/pitch_loader.py
"""
Pitch data loader — provides startup pitch data to FUSION agents.
Agents call load_deal_brief(section) to fetch the relevant portion
of the pitch deck for their domain analysis.
"""
import json
import os
import logging
from langchain_core.tools import tool

logger = logging.getLogger("fusion.pitch_loader")

_PITCH_CACHE: dict = {}
_DEFAULT_PITCH = "novapay_pitch.json"


def _load_pitch_file(filename: str = None) -> dict:
    """Load pitch JSON from the data/ directory. Cached after first load.

    When no filename is given, resolves the active pitch from sim_state:
    active_pitch_file first, then the pitch_{incident_id}.json convention."""
    if filename is None:
        try:
            from api.state import sim_state
            data_dir = os.path.join(os.path.dirname(__file__), "../data")
            active = getattr(sim_state, "active_pitch_file", None)
            if active and os.path.exists(os.path.join(data_dir, active)):
                filename = active
            elif sim_state.active_incident_id:
                uploaded_filename = f"pitch_{sim_state.active_incident_id}.json"
                if os.path.exists(os.path.join(data_dir, uploaded_filename)):
                    filename = uploaded_filename
                else:
                    filename = _DEFAULT_PITCH
            else:
                filename = _DEFAULT_PITCH
        except Exception:
            filename = _DEFAULT_PITCH

    if filename in _PITCH_CACHE:
        return _PITCH_CACHE[filename]

    if os.path.isabs(filename):
        path = filename
    else:
        data_dir = os.path.join(os.path.dirname(__file__), "../data")
        path = os.path.join(data_dir, filename)

    try:
        with open(path, "r") as f:
            data = json.load(f)
        _PITCH_CACHE[filename] = data
        logger.info(f"[PitchLoader] Loaded pitch: {filename}")
        return data
    except FileNotFoundError:
        logger.error(f"[PitchLoader] Pitch file not found: {path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"[PitchLoader] Invalid JSON in {path}: {e}")
        return {}


def clear_pitch_cache():
    """Clear the pitch cache so the next load picks up a newly uploaded file."""
    _PITCH_CACHE.clear()


# ─── LangChain tools for agents ──────────────────────────────────────────────

@tool("load_deal_brief")
def load_deal_brief(section: str = "all") -> str:
    """Load the startup pitch data for due diligence analysis.

    Args:
        section: Which section to retrieve. Options:
            'all'        - Full pitch (use sparingly — large)
            'company'    - Company overview and claims
            'financials' - Revenue, burn, unit economics, customer breakdown
            'legal'      - Litigation, IP, regulatory compliance
            'technical'  - Tech stack, security posture, architecture
            'market'     - Market size, competitors, regulatory trends
            'team'       - Founding team backgrounds and gaps
            'deal_summary' - Raise amount, valuation, use of funds

    Returns:
        JSON string of the requested pitch section.
    """
    data = _load_pitch_file()
    if not data:
        return json.dumps({"error": "No pitch data loaded. Check data/novapay_pitch.json exists."})

    if section == "all":
        return json.dumps(data, indent=2)

    if section in data:
        return json.dumps(data[section], indent=2)

    # Fuzzy fallback — return full data if section not found
    logger.warning(f"[PitchLoader] Section '{section}' not found — returning full pitch.")
    return json.dumps(data, indent=2)


@tool("get_company_name")
def get_company_name() -> str:
    """Get the name of the startup being evaluated."""
    data = _load_pitch_file()
    return data.get("company", {}).get("name", "Unknown Company")


@tool("get_red_flags")
def get_red_flags(domain: str = "all") -> str:
    """Get the pre-catalogued red flags for a specific domain.

    Args:
        domain: 'financials', 'legal', 'technical', 'market', or 'all'

    Returns:
        List of red flag strings for the specified domain.
    """
    data = _load_pitch_file()

    if domain == "all":
        all_flags = []
        for section in ["financials", "legal", "technical", "market"]:
            section_data = data.get(section, {})
            flags = section_data.get("red_flags", [])
            all_flags.extend([f"[{section.upper()}] {f}" for f in flags])
        return json.dumps(all_flags, indent=2)

    section_data = data.get(domain, {})
    flags = section_data.get("red_flags", [])
    return json.dumps(flags, indent=2)


@tool("get_calculated_scores")
def get_calculated_scores() -> str:
    """Get the mathematically calculated risk scores, coverage, evidence quality, and confidence metrics for the current startup.
    Use this to get the exact scores to populate the FUSION Investment Committee Decision card.
    
    Returns:
        JSON string containing the risk scores, weighted score, verdict, coverage, and confidence.
    """
    from core.diligence_engine import run_diligence_calculations
    data = _load_pitch_file()
    if not data:
        return json.dumps({"error": "No pitch data loaded."})
    calc = run_diligence_calculations(data)
    return json.dumps({
        "company_name": calc.get("company_name"),
        "financial_risk_score": calc.get("fin_score"),
        "legal_risk_score": calc.get("leg_score"),
        "technical_risk_score": calc.get("tech_score"),
        "market_risk_score": calc.get("mkt_score"),
        "weighted_risk_score": calc.get("weighted_score"),
        "verdict": calc.get("verdict"),
        "coverage_score": calc.get("coverage_score"),
        "evidence_quality_score": calc.get("evidence_quality_score"),
        "verdict_confidence": calc.get("verdict_confidence"),
        "deal_readiness_score": calc.get("deal_readiness_score"),
        "deal_readiness_status": calc.get("deal_readiness_status"),
        "missing_gaps": calc.get("missing_gaps"),
        "contradictions_count": len(calc.get("contradictions", []))
    }, indent=2)
