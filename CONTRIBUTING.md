# Contributing to FUSION

Thank you for your interest in FUSION. This project was built for the Band of Agents Hackathon 2026 by Team Agent Core.

---

## Project Structure

- **`agents/`** — The 5 specialized VC boardroom partner implementations.
- **`core/`** — The core engine: diligence calculations, ReportLab PDF generators, Shared Memory Graph (Graphify), LLM router, and Event Bus.
- **`api/`** — FastAPI REST & WebSocket backend routing.
- **`data/`** — Startup data room pitches (JSON and Markdown files).
- **`frontend/`** — Next.js war room boardroom dashboard.

---

## Adding a New Partner Agent

To expand the Investment Committee with another specialist (e.g., a "Product Partner" or "Operations Partner"):

1. **Create Agent File**: Create `agents/product_partner.py` extending `BaseAgent` and define its persona prompt and tools:
   ```python
   from core.base_agent import BaseAgent
   from core.pitch_loader import load_deal_brief, get_calculated_scores
   ```
2. **Define Agent Logic**: Add `product_partner` to `run.py` to launch it alongside the other partners.
3. **Register Band Credentials**: Add the agent's ID and room credentials to `agent_config.yaml` and `scripts/setup_band_rooms.py`.
4. **Update briefing flow**: Update `agents/managing_partner.py` to brief the new partner and await its report.
5. **Update Frontend Graph**: Add a new node to the boardroom Roundtable visualizer in `frontend/pages/index.tsx`.

---

## Code Style & Conventions

- **Python**: Follow PEP 8 and use type hints where possible.
- **Async/Await**: Use asynchronous calls (`async/await`) for all database operations, LLM calls, and network transfers.
- **Agent Communication**: Agents must always coordinate using the Band platform. Use `thenvoi_send_message` to @mention partners and `thenvoi_send_event` to broadcast status updates to the dashboard.
- **Deterministic Metrics**: Always query the `get_calculated_scores` tool inside partner agents for scores. Do not invent risk grades in the LLM.

---

## Running Tests

Before submitting a pull request, run the test suites to ensure everything is operational:

```bash
# Core suite (imports, endpoints, files, mock run check)
python test_fusion.py

# Tier A feature suite (pdf generation, reset sync, upload parsing)
python test_tier_a_features.py
```

---

## License

MIT — see [LICENSE](LICENSE)
