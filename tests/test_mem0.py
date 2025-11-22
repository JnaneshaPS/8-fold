import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from mem0 import MemoryClient

load_dotenv()


def test_mem0():
    print("Testing Mem0 API...")
    
    api_key = os.getenv("MEM0_API_KEY")
    if not api_key:
        print("✗ Failed: MEM0_API_KEY not set in environment")
        return
    
    try:
        client = MemoryClient(api_key=api_key)
        
        test_user_id = "test_user_123"
        
        print("  1. Adding memory...")
        messages = [
            {"role": "user", "content": "I work at Stripe as a Sales Engineer"},
            {"role": "assistant", "content": "Great! I'll remember that you work at Stripe as a Sales Engineer."}
        ]
        
        result = client.add(messages, user_id=test_user_id)
        print(f"     ✓ Memory added: {result}")
        
        print("\n  2. Searching memory...")
        search_result = client.search(
            "Where do I work?",
            filters={"user_id": test_user_id}
        )
        print(f"     ✓ Search results: {search_result}")
        
        print("\n✓ Mem0 test completed successfully!")
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    test_mem0()

