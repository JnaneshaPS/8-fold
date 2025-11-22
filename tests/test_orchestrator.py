import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def test_database_connection():
    print("=" * 60)
    print("TEST 1: Database Connection & Setup")
    print("=" * 60)
    
    from backend.db.client import get_session
    from backend.db.cruds import init_db, create_persona, list_personas
    from backend.db.models import PersonaCreate
    
    try:
        init_db()
        print("✓ Database tables created/verified")
        
        with get_session() as db:
            personas = list_personas(db)
            print(f"✓ Found {len(personas)} existing personas")
            
            test_persona = PersonaCreate(
                name="Test Sales Engineer",
                role="Sales Engineer",
                company="Test Corp",
                region="US",
                goal="Test goal",
                notes="Test persona for orchestrator"
            )
            
            created = create_persona(db, test_persona)
            print(f"✓ Created test persona: {created.name} (ID: {created.id})")
            
            return created.id
            
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


async def test_research_orchestrator(persona_id):
    print("\n" + "=" * 60)
    print("TEST 2: Research Orchestrator")
    print("=" * 60)
    
    from backend.orchestrator import OrchestratorFactory
    
    try:
        orchestrator = OrchestratorFactory.create_research_orchestrator(
            user_id="test_user_123",
            persona_id=persona_id
        )
        
        print(f"✓ Orchestrator created with persona: {orchestrator.context.persona.name}")
        print(f"  Company: {orchestrator.context.persona.company}")
        print(f"  Role: {orchestrator.context.persona.role}")
        
        print("\n  Running research on 'Stripe'...")
        report = await orchestrator.run_full_research(
            company_name="Stripe",
            save_to_db=True
        )
        
        print(f"\n✓ Research completed!")
        print(f"  Company: {report.fundamentals.profile.company_name}")
        print(f"  HQ: {report.fundamentals.profile.headquarters}")
        print(f"  Industry: {report.fundamentals.profile.industry}")
        print(f"  Leaders found: {len(report.leadership.leaders)}")
        print(f"  News items: {len(report.news.items)}")
        print(f"  Products: {len(report.tech_services.products_and_services)}")
        print(f"  Opportunities: {len(report.strategy.opportunities_for_me)}")
        print(f"  Stock data: {'Yes' if report.stock else 'No (private company)'}")
        
        print(f"\n  Why it matters:")
        print(f"  {report.strategy.why_it_matters[:150]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Research orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_chat_orchestrator(persona_id):
    print("\n" + "=" * 60)
    print("TEST 3: Chat Orchestrator")
    print("=" * 60)
    
    from backend.orchestrator import OrchestratorFactory
    
    try:
        orchestrator = OrchestratorFactory.create_chat_orchestrator(
            user_id="test_user_123",
            persona_id=persona_id
        )
        
        print(f"✓ Chat orchestrator created")
        
        print("\n  Chat 1: Tell me about payment processing companies")
        response1 = await orchestrator.chat("Tell me about payment processing companies")
        print(f"  Response: {response1[:200]}...")
        
        print("\n  Chat 2: What should I know about Stripe?")
        response2 = await orchestrator.chat("What should I know about Stripe?")
        print(f"  Response: {response2[:200]}...")
        
        print("\n✓ Chat orchestrator working")
        print("⚠ Note: Chat history is NOT maintained between calls in current implementation")
        
        return True
        
    except Exception as e:
        print(f"✗ Chat orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_compare_orchestrator(persona_id):
    print("\n" + "=" * 60)
    print("TEST 4: Compare Orchestrator")
    print("=" * 60)
    
    from backend.orchestrator import OrchestratorFactory
    
    try:
        orchestrator = OrchestratorFactory.create_compare_orchestrator(
            user_id="test_user_123",
            persona_id=persona_id
        )
        
        print(f"✓ Compare orchestrator created")
        
        print("\n  Comparing: Stripe vs Razorpay")
        result = await orchestrator.compare_companies(
            company_a="Stripe",
            company_b="Razorpay",
            use_cached=True
        )
        
        print(f"\n✓ Comparison completed!")
        print(f"  Company A: {result.company_a['name']}")
        print(f"  Company B: {result.company_b['name']}")
        print(f"\n  Recommendation:")
        print(f"  {result.recommendation}")
        
        print(f"\n  Comparison summary:")
        print(f"  {result.comparison_summary[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Compare orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mem0_integration():
    print("\n" + "=" * 60)
    print("TEST 5: Mem0 Integration")
    print("=" * 60)
    
    from backend.memory.mem0_client import add_memory, search_memory
    
    try:
        test_user = "test_user_123"
        
        print("  Adding memory...")
        add_memory(
            messages=[
                {"role": "user", "content": "I researched Stripe"},
                {"role": "assistant", "content": "Stripe is a payment processing platform"}
            ],
            user_id=test_user,
            metadata={"test": "orchestrator"}
        )
        print("✓ Memory added (processing in background)")
        
        print("\n  Searching memory...")
        results = search_memory(
            query="Stripe research",
            user_id=test_user,
            limit=3
        )
        print(f"✓ Search completed: {len(results.get('results', []))} results")
        
        return True
        
    except Exception as e:
        print(f"✗ Mem0 integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "=" * 60)
    print("ORCHESTRATOR COMPREHENSIVE TEST")
    print("=" * 60 + "\n")
    
    try:
        persona_id = await test_database_connection()
        
        research_ok = await test_research_orchestrator(persona_id)
        
        chat_ok = await test_chat_orchestrator(persona_id)
        
        compare_ok = await test_compare_orchestrator(persona_id)
        
        mem0_ok = await test_mem0_integration()
        
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        print(f"Database: ✓")
        print(f"Research Orchestrator: {'✓' if research_ok else '✗'}")
        print(f"Chat Orchestrator: {'✓' if chat_ok else '✗'}")
        print(f"Compare Orchestrator: {'✓' if compare_ok else '✗'}")
        print(f"Mem0 Integration: {'✓' if mem0_ok else '✗'}")
        
        print("\n" + "=" * 60)
        print("CRITICAL ISSUE FOUND:")
        print("=" * 60)
        print("⚠ Chat orchestrator does NOT maintain conversation history")
        print("⚠ Each chat call is isolated - no multi-turn context")
        print("⚠ This needs to be fixed for proper chat functionality")
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

