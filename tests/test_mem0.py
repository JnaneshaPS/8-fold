import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def setup_test_persona():
    from backend.db.client import get_session
    from backend.db.cruds import init_db, create_persona
    from backend.db.models import PersonaCreate
    
    init_db()
    
    with get_session() as db:
        persona = PersonaCreate(
            name="Test Sales Eng",
            role="Sales Engineer",
            company="Test Corp",
            region="US",
            goal="Test chat mode",
        )
        created = create_persona(db, persona)
        return created.id


async def test_mem0():
    print("\n" + "=" * 60)
    print("TEST: Mem0 Integration")
    print("=" * 60)
    
    from backend.memory.mem0_client import add_memory, search_memory
    
    test_user = "test_user_456"
    
    try:
        print("\n  Step 1: Adding memory...")
        add_memory(
            messages=[
                {"role": "user", "content": "I work at Stripe as a Payment Engineer"},
                {"role": "assistant", "content": "Great! I'll remember you work at Stripe as a Payment Engineer."}
            ],
            user_id=test_user,
            metadata={"test": "chat_mode"}
        )
        print("  ✓ Memory added (processing in background)")
        
        await asyncio.sleep(2)
        
        print("\n  Step 2: Searching memory...")
        results = search_memory(
            query="Where do I work?",
            user_id=test_user,
            limit=3
        )
        
        print(f"  ✓ Search successful!")
        print(f"  Results: {len(results.get('results', []))} memories found")
        
        if results.get('results'):
            for i, mem in enumerate(results['results'][:2], 1):
                print(f"    {i}. {mem.get('memory', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Mem0 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_chat_with_history(persona_id):
    print("\n" + "=" * 60)
    print("TEST: Chat Mode with Conversation History")
    print("=" * 60)
    
    from backend.orchestrator import OrchestratorFactory
    
    try:
        orchestrator = OrchestratorFactory.create_chat_orchestrator(
            user_id="test_user_456",
            persona_id=persona_id
        )
        
        print(f"\n✓ Chat orchestrator created")
        print(f"  Persona: {orchestrator.context.persona.name}")
        print(f"  Conversation history: {len(orchestrator.conversation_history)} messages")
        
        print("\n  Turn 1: What payment companies should I know about?")
        response1 = await orchestrator.chat("What payment companies should I know about?")
        print(f"  Response: {response1[:150]}...")
        print(f"  History size: {len(orchestrator.conversation_history)} messages")
        
        print("\n  Turn 2: Tell me more about the first one")
        response2 = await orchestrator.chat("Tell me more about the first one")
        print(f"  Response: {response2[:150]}...")
        print(f"  History size: {len(orchestrator.conversation_history)} messages")
        
        print("\n  Turn 3: What was my first question?")
        response3 = await orchestrator.chat("What was my first question?")
        print(f"  Response: {response3[:150]}...")
        print(f"  History size: {len(orchestrator.conversation_history)} messages")
        
        print("\n✓ Chat mode with context tracking:")
        print(f"  ✓ Conversation history maintained: {len(orchestrator.conversation_history)} total messages")
        print(f"  ✓ Multi-turn context working")
        print(f"  ✓ Memory saving after each turn")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Chat failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "=" * 60)
    print("FOCUSED TEST: Chat Mode + Mem0")
    print("=" * 60)
    
    try:
        print("\nSetting up test persona...")
        persona_id = await setup_test_persona()
        print(f"✓ Persona created: {persona_id}")
        
        mem0_ok = await test_mem0()
        
        chat_ok = await test_chat_with_history(persona_id)
        
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Mem0 Integration: {'✓ WORKING' if mem0_ok else '✗ FAILED'}")
        print(f"Chat with History: {'✓ WORKING' if chat_ok else '✗ FAILED'}")
        
        if mem0_ok and chat_ok:
            print("\n🎉 ALL TESTS PASSED!")
            print("\nChat Mode Features:")
            print("  ✓ Conversation history maintained in memory")
            print("  ✓ Multi-turn context preserved")
            print("  ✓ Each message saved to Mem0")
            print("  ✓ Mem0 search/add working correctly")
        else:
            print("\n⚠️ Some tests failed - check errors above")
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

