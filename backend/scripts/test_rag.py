import asyncio
import logging
import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag.chat import ChatOrchestrator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    q = "Why do users order fruits and vegetables on Blinkit, and what are their main complaints?"
    print(f"Asking: {q}\n")
    
    res = await ChatOrchestrator.chat(q)
    
    print("\n" + "="*50)
    print("--- ANSWER ---")
    print(res.answer)
    print("\n--- CITATIONS ---")
    for cit in res.citations:
        print(f"- [{cit['source']}] {cit['id']}: {cit['snippet']}")
    print("\n--- SOURCES BREAKDOWN ---")
    print(res.source_breakdown)
    print(f"\nLLM Used: {res.llm_used}")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
