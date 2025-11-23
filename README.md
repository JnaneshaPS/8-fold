# 8-Fold Assistant

AI-powered Company Research Assistant (Account Plan Generator) for B2B personas.

## Feature Checklist

| Requirement | Coverage |
|-------------|----------|
| Gather information from multiple sources and synthesize findings | Research mode orchestrates Fundamentals, Leadership, Tech, News, Strategy, and Visualization agents powered by Perplexity, Exa MCP, and finance APIs. |
| Provide updates during research | Chat mode (text) and Realtime mode (voice) sit on top of the same persona + Mem0 memory. Users can ask the assistant mid-run (“Should we dig deeper on X?”) and it will summarize current findings or trigger another research pass. |
| Allow users to update sections of the generated account plan | Reports are persisted in NeonDB plus Mem0. Users can re-run Research or use Chat to overwrite/augment sections (e.g., “Update opportunities to highlight fraud surface on BNPL”). |
| Interaction Mode: Chat or voice | Streamlit sidebar lets users pick **Assistant** (Chat/Research/Compare) or **Realtime Voice** (WebRTC voice session with OpenAI Realtime API). |

## Architecture

- **Frontend**: Streamlit (text assistant + realtime voice page)
- **Backend**: Python with OpenAI Agents SDK
- **DB**: Neon/PostgreSQL
- **Memory**: Mem0
- **External sources**: Perplexity Sonar-Pro, Exa MCP (web search), Alpha Vantage/finance API, OpenAI Realtime

## User Experience

1. **Personas**: Create/select a persona (role, company, goal). Persona context drives every agent.
2. **Assistant Experience**  
   - *Chat*: Conversational Q&A; can summarize, gather updates, or ask clarifying questions mid research.  
   - *Research*: Launches the full orchestrator to gather data, synthesizes a detailed plan, saves it to Neon + Mem0.  
   - *Compare*: Compares two companies by reusing cached reports or running lightweight research.  
3. **Realtime Voice**: WebRTC mic capture + OpenAI Realtime session using persona context. No tokens persist beyond the session; Connect/Stop buttons control media.

## Running the App

```bash
uv sync
python -c "from backend.db.cruds import init_db; init_db()"
streamlit run app.py
```

Environment variables:
```
OPENAI_API_KEY=...
PERPLEXITY_API_KEY=...
MEM0_API_KEY=...
NEON_DATABASE_URL=...
EXA_API_KEY=...
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview (optional)
OPENAI_REALTIME_VOICE=alloy (optional)
```

## Key Modules

```
backend/
├── orchestrator.py          # Chat/Research/Compare orchestrators
├── agents/                  # Fundamentals, Leadership, Market News, Tech/Services, Persona Strategy, Visualization
├── realtime/session.py      # Persona-aware realtime session builder
├── memory/mem0_client.py    # Mem0 add/search helpers
└── db/                      # Personas, reports, compare sessions

ui/
├── chat_page.py             # Chat + Research + Compare UI
├── realtime_page.py         # Realtime WebRTC widget
└── __init__.py
```

## Programmatic Examples

### Running Research
```python
from backend.orchestrator import OrchestratorFactory
import asyncio

async def main():
    orch = OrchestratorFactory.create_research_orchestrator(
        user_id="demo",
        persona_id="uuid-persona"
    )
    report = await orch.run_full_research(request="Research Stripe", save_to_db=True)
    print(report.strategy.why_it_matters)

asyncio.run(main())
```

### Chatting
```python
async def chat():
    chat_orch = OrchestratorFactory.create_chat_orchestrator(
        user_id="demo",
        persona_id="uuid-persona"
    )
    print(await chat_orch.chat("Give me a quick update on Stripe vs Razorpay."))

asyncio.run(chat())
```

### Comparing Companies
```python
async def compare():
    compare_orch = OrchestratorFactory.create_compare_orchestrator(
        user_id="demo",
        persona_id="uuid-persona"
    )
    result = await compare_orch.compare_companies("Stripe", "Razorpay")
    print(result.recommendation)

asyncio.run(compare())
```

## How “updates” work

- Reports are persisted; rerunning Research overwrites/extends the JSON per persona/company.
- Chat or Realtime can summarize current sections (“Show me the latest opportunities”) or rewrite them (“Replace risks with X/Y”). Those instructions flow through the Persona Strategy agent and Mem0 so future runs keep the adjustments.

## Realtime Voice Quickstart

1. Run `streamlit run app.py`.
2. Select a persona → choose **Realtime Voice** in the sidebar.
3. Click **Refresh token** if needed, then **Connect** (allow microphone). Speak naturally; the assistant replies via audio and logs transcripts.
