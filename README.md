# 🌿 FoodFlow AI

**Autonomous Food Rescue Engine** — Cornell Claude Builders Club Hackathon 2026

AI-powered surplus prediction and real-time redistribution — connecting institutions to food banks before the food ever hits the bin.

## How it works

1. **Predict** surplus food 2 hours before closing using POS/inventory data
2. **Match** automatically via Claude tool_use agent (6 autonomous steps in ~4 seconds)
3. **Dispatch** volunteer driver via SMS, log pickup, generate ESG report

## Quick Start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-your_key_here
uvicorn main:app --reload --port 8000
# Open http://localhost:8000
```

## Architecture

```
main.py          FastAPI app — dashboard + API routes
agent.py         Claude claude-sonnet-4-6 tool_use agent loop
tools.py         6 tool functions: inventory, volunteers, route, compliance, dispatch
database.py      SQLite + seed data (Cornell Statler Hall)
report.py        ESG PDF auto-generator (reportlab)
templates/       Jinja2 dashboard (auto-refreshes every 10s)
static/          CSS styles
```

## The 6-Tool Agent Loop

```
[TOOL: check_inventory]        → confirm surplus details
[TOOL: check_foodbank_capacity]→ find accepting food bank
[TOOL: query_volunteers]       → find drivers near supplier
[TOOL: calculate_route]        → estimate ETA
[TOOL: verify_compliance]      → Bill Emerson Act check
[TOOL: dispatch_pickup]        → send SMS + log pickup
```

## Business Model

- **SaaS**: $99 / $299 / $2,500/mo tiers
- **Success Fee**: 2% of food value rescued
- **ESG Reports**: $500/quarter auto-generated PDF

## Key Metrics

| Metric | Value |
|--------|-------|
| LTV:CAC (Enterprise) | 380x |
| CAC Payback | 8 days |
| Gross Margin | 78% |
| NRR Target | 115% |
| Year 3 ARR | $1.82M |

## TAM/SAM/SOM

- TAM: $2.2B (all US food institutions)
- SAM: $426M (urban universities + restaurant groups)
- SOM: $1.82M Year 3 (0.43% of SAM — conservative)

## Impact (Year 3 projection)

- 12M lbs food rescued annually
- 7.2M meals served
- 65 institutions across 3 cities

---

Built at Cornell Claude Builders Club Hackathon · April 25, 2026  
Powered by [Anthropic Claude](https://anthropic.com) · FastAPI · SQLite · reportlab
