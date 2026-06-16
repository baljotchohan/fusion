# Contributing to ARGUS

Thanks for your interest in ARGUS. This project was built for the Band of Agents Hackathon 2026 by Team Agent Core.

## Development Setup

Follow the full setup guide in [SETUP.md](SETUP.md).

## Project Structure

- `agents/` — The 9 Band agents (one file per agent)
- `core/` — Shared utilities (MITRE lookup, CVE lookup, Band client, event bus)
- `api/` — FastAPI backend
- `data/` — Digital twin and static data
- `frontend/` — Next.js War Room dashboard

## Adding a New Agent

1. Create `agents/your_agent.py` extending `BaseAgent`
2. Define a `StateGraph` with typed state in `core/`
3. Register in `run.py`
4. Add Band room to `scripts/setup_band_rooms.py`
5. Update Incident Commander routing in `agents/incident_commander.py`
6. Add node to React Flow graph in `frontend/components/AgentGraph.tsx`

## Code Style

- Python: follow PEP 8, use type hints everywhere
- Use `async/await` for all I/O operations
- Every agent must use `thenvoi_send_message` to communicate — never plain print or return

## Running Tests

```bash
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE)
