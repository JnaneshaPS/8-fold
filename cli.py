import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from backend.orchestrator import OrchestratorFactory
from backend.db.client import get_session
from backend.db.cruds import init_db, create_persona, list_personas
from backend.db.models import PersonaCreate

load_dotenv()


async def setup_persona():
    init_db()
    
    with get_session() as db:
        personas = list_personas(db)
        
        if personas:
            print("\nExisting Personas:")
            for i, p in enumerate(personas, 1):
                print(f"{i}. {p.name} ({p.role} at {p.company})")
            
            choice = input("\nUse existing? (number or 'n'): ").strip()
            
            if choice.lower() != 'n' and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(personas):
                    return personas[idx].id
        
        print("\nCreate Persona:")
        name = input("  Name: ").strip() or "User"
        role = input("  Role: ").strip() or "Sales"
        company = input("  Company: ").strip() or "Corp"
        region = input("  Region: ").strip() or "US"
        goal = input("  Goal: ").strip() or "Research"
        
        persona = PersonaCreate(
            name=name,
            role=role,
            company=company,
            region=region,
            goal=goal,
        )
        
        created = create_persona(db, persona)
        print(f"✓ Created: {created.name}")
        return created.id


async def main():
    print("="*70)
    print("8-FOLD ASSISTANT CLI")
    print("="*70)
    print("\nCommands:")
    print("  @company       -> Research Mode")
    print("  #A vs B        -> Compare Mode")
    print("  normal text    -> Chat Mode")
    print("  exit           -> Quit")
    print("  clear          -> Clear chat history")
    print("="*70)
    
    persona_id = await setup_persona()
    
    chat_orch = OrchestratorFactory.create_chat_orchestrator("cli_user", persona_id)
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == 'exit':
            print("\n✓ Goodbye!")
            break
        
        if user_input.lower() == 'clear':
            chat_orch.conversation_history = []
            print("✓ Chat cleared")
            continue
        
        if user_input.startswith('@'):
            company = user_input[1:].strip()
            if not company:
                print("Usage: @CompanyName")
                continue
            
            print(f"\n[RESEARCH MODE: {company}]")
            try:
                orch = OrchestratorFactory.create_research_orchestrator("cli_user", persona_id)
                report = await orch.run_full_research(company, save_to_db=True)
                
                print(f"\n✓ {report.fundamentals.profile.company_name}")
                print(f"  HQ: {report.fundamentals.profile.headquarters}")
                print(f"  Leaders: {len(report.leadership.leaders)}")
                print(f"  News: {len(report.news.items)}")
                print(f"  Opportunities: {len(report.strategy.opportunities_for_me)}")
                print(f"\nWhy it matters:\n{report.strategy.why_it_matters[:300]}...")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        elif user_input.startswith('#'):
            parts = user_input[1:].strip().split(' vs ')
            if len(parts) != 2:
                print("Usage: #CompanyA vs CompanyB")
                continue
            
            company_a, company_b = parts[0].strip(), parts[1].strip()
            print(f"\n[COMPARE MODE: {company_a} vs {company_b}]")
            try:
                orch = OrchestratorFactory.create_compare_orchestrator("cli_user", persona_id)
                comp = await orch.compare_companies(company_a, company_b, use_cached=True)
                
                print(f"\nRecommendation:\n{comp.recommendation}")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        else:
            print(f"\n[CHAT MODE]")
            try:
                response = await chat_orch.chat(user_input)
                print(f"\nAssistant:\n{response}")
                print(f"\n[History: {len(chat_orch.conversation_history)} messages]")
            except Exception as e:
                print(f"✗ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
