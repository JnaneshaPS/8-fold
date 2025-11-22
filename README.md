# 8-Fold Assistant

AI-powered Account Research & Planning Assistant for B2B personas.

## Architecture

The application is built using:
- **Frontend**: Streamlit
- **Backend**: Python with OpenAI Agents SDK
- **Database**: NeonDB (PostgreSQL)
- **Memory**: Mem0
- **APIs**: Perplexity, Exa (via MCP), Finance APIs

## Core Components

### Orchestrators

The system has three main orchestrators:

1. **ResearchOrchestrator**: Conducts deep company research
2. **ChatOrchestrator**: Handles conversational interactions
3. **CompareOrchestrator**: Compares two companies

### Agents

Specialized agents handle different research aspects:
- **Fundamentals Agent**: Company profile, key numbers, business model
- **Leadership Agent**: Key decision makers with LinkedIn profiles
- **Market News Agent**: Recent news and sentiment
- **Tech Services Agent**: Products, services, and tech stack
- **Persona Strategy Agent**: Persona-specific insights and opportunities
- **Visualization Agent**: Stock price charts for public companies

## Usage

### Research Mode

```python
from backend.orchestrator import OrchestratorFactory
import asyncio

async def run_research():
    orchestrator = OrchestratorFactory.create_research_orchestrator(
        user_id="user123",
        persona_id="uuid-of-persona"
    )
    
    report = await orchestrator.run_full_research(
        company_name="Stripe",
        website="https://stripe.com",
        save_to_db=True
    )
    
    print(f"Research complete for {report.fundamentals.profile.company_name}")
    print(f"Opportunities: {len(report.strategy.opportunities_for_me)}")

asyncio.run(run_research())
```

### Chat Mode

```python
async def chat_example():
    orchestrator = OrchestratorFactory.create_chat_orchestrator(
        user_id="user123",
        persona_id="uuid-of-persona"
    )
    
    response = await orchestrator.chat("Tell me about payment processing companies in India")
    print(response)

asyncio.run(chat_example())
```

### Compare Mode

```python
async def compare_example():
    orchestrator = OrchestratorFactory.create_compare_orchestrator(
        user_id="user123",
        persona_id="uuid-of-persona"
    )
    
    result = await orchestrator.compare_companies(
        company_a="Stripe",
        company_b="Razorpay",
        use_cached=True
    )
    
    print(result.recommendation)
    print(result.comparison_summary)

asyncio.run(compare_example())
```

## Database Models

### Persona
Represents a user's selling persona with role, company, region, and goals.

### Report
Stores full research reports with all sections as JSON.

### CompareSession
Records company comparison results.

## Environment Variables

Required environment variables:
```
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=...
MEM0_API_KEY=...
NEON_DATABASE_URL=postgresql://...
EXA_API_KEY=...
```

## Project Structure

```
backend/
├── agents/           # Specialized research agents
├── db/              # Database models and CRUD operations
├── external/        # External API clients
├── mcp/             # MCP client integrations
├── memory/          # Mem0 memory management
├── utils/           # Utilities (PDF export, scraping)
└── orchestrator.py  # Main orchestration logic

ui/
├── chat_page.py
├── research_page.py
└── compare_research.py
```

## Development

Install dependencies:
```bash
uv sync
```

Initialize database:
```bash
python -c "from backend.db.cruds import init_db; init_db()"
```

Run Streamlit app:
```bash
streamlit run app.py
```

