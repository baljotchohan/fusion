# core/demo_registry.py
"""
Central registry of the demo deals shown on the FUSION dashboard.

Each entry binds a display card to a real pitch JSON in data/ so that:
  - the dashboard can render a card + raw-data preview before any agent runs, and
  - /api/trigger-deal can resolve a company name to the correct pitch file
    (so the committee actually analyzes THAT company, not the default).

The `expected_verdict` is informational (drawn from the deterministic engine);
the live verdict is always computed by core/diligence_engine at run time.
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("fusion.demo_registry")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Order here is the order the cards render on the dashboard.
DEMO_DEALS: List[Dict[str, Any]] = [
    {
        "id": "helios",
        "company_name": "Helios AI",
        "pitch_file": "helios_pitch.json",
        "sector": "AI Dev Tools / LLM Observability",
        "stage": "Series A",
        "raise_amount": "$12M",
        "tagline": "Observability + evals for teams shipping LLM apps. Eval scoring wired into CI.",
        "expected_verdict": "INVEST",
        "accent": "emerald",
    },
    {
        "id": "gridflow",
        "company_name": "GridFlow Energy",
        "pitch_file": "gridflow_pitch.json",
        "sector": "Climate / Grid Optimization",
        "stage": "Series A",
        "raise_amount": "$15M",
        "tagline": "Physics-informed forecasting for utilities — cuts curtailment and peak-demand cost.",
        "expected_verdict": "INVEST",
        "accent": "sky",
    },
    {
        "id": "cadence",
        "company_name": "Cadence Health",
        "pitch_file": "cadence_pitch.json",
        "sector": "Healthtech / Remote Patient Monitoring",
        "stage": "Series A",
        "raise_amount": "$11M",
        "tagline": "RPM triage that cuts alert fatigue 44% — strong clinically, concentrated financially.",
        "expected_verdict": "CONDITIONAL",
        "accent": "amber",
    },
    {
        "id": "novapay",
        "company_name": "NovaPay Inc",
        "pitch_file": "novapay_pitch.json",
        "sector": "Fintech / Buy Now Pay Later",
        "stage": "Series A",
        "raise_amount": "$10M",
        "tagline": "BNPL with planted red flags: 78% client concentration, patent suit, EOL stack, plaintext PII.",
        "expected_verdict": "PASS",
        "accent": "rose",
    },
]

_BY_ID = {d["id"]: d for d in DEMO_DEALS}


def list_demos() -> List[Dict[str, Any]]:
    """Lightweight card metadata for the dashboard (no raw pitch payload)."""
    return [
        {k: v for k, v in d.items() if k != "pitch_file"} | {"pitch_file": d["pitch_file"]}
        for d in DEMO_DEALS
    ]


def get_demo(demo_id: str) -> Optional[Dict[str, Any]]:
    return _BY_ID.get((demo_id or "").lower())


def resolve_pitch_file(company_name: Optional[str]) -> Optional[str]:
    """Map a company name (or demo id) to its pitch JSON filename.
    Returns None if no demo matches, so callers can fall back to the default."""
    if not company_name:
        return None
    key = str(company_name).strip().lower()
    if key in _BY_ID:
        return _BY_ID[key]["pitch_file"]
    for d in DEMO_DEALS:
        cn = d["company_name"].lower()
        if key == cn or key in cn or cn in key:
            return d["pitch_file"]
    return None


def load_demo_pitch(demo_id: str) -> Optional[Dict[str, Any]]:
    """Full raw pitch JSON for the preview panel."""
    d = get_demo(demo_id)
    if not d:
        return None
    path = os.path.join(_DATA_DIR, d["pitch_file"])
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load demo pitch {d['pitch_file']}: {e}")
        return None
