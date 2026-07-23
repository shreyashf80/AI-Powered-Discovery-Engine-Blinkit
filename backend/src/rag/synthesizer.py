import logging
import json
from typing import List
from src.shared.schemas import RetrievedItem, SynthesisResult
from src.shared.llm import llm_client

logger = logging.getLogger(__name__)

class Synthesizer:
    SYSTEM_PROMPT = """You are an expert qualitative researcher analyzing user feedback for Blinkit.
You will be provided with a user's question and a list of retrieved snippets from various sources (Reddit, App Store, Play Store, YouTube).

YOUR GOAL:
Synthesize a clear, structured answer based ONLY on the provided context. 

RULES:
1. CITATIONS: Every factual claim MUST cite the specific source snippet using inline markdown links, formatted exactly as: [Source Name](id). Replace "Source Name" with the actual source and "id" with the review ID.
2. CONTRADICTIONS: If the evidence splits or is contradictory, present both sides.
3. QUANTIFICATION: If you make quantified claims, explicitly state the proportion from the context.
4. NO HALLUCINATION: If the context lacks data to answer the question, state that you don't have enough data.

OUTPUT FORMAT:
Return ONLY a valid JSON object. Do not wrap in markdown blockquotes like ```json.
{
  "answer": "Your detailed markdown-formatted answer with [Source Name](id) citations.",
  "citations": [
     {"id": "the_review_id", "snippet": "exact snippet text", "source": "Source Name"}
  ]
}
"""

    @classmethod
    async def synthesize(cls, question: str, retrieved: List[RetrievedItem]) -> SynthesisResult:
        if not retrieved:
            return SynthesisResult(
                answer="I couldn't find any relevant insights for that question in the database.",
                citations=[],
                source_breakdown={},
                llm_used="none"
            )
            
        context_blocks = []
        source_counts = {}
        
        for item in retrieved:
            source = item.source
            source_counts[source] = source_counts.get(source, 0) + 1
            
            context_blocks.append(f"--- ID: {item.id} | SOURCE: {source} ---\nSnippet: {item.source_snippet}\nMetadata: {json.dumps(item.metadata)}")
            
        user_prompt = f"USER QUESTION: {question}\n\nRETRIEVED CONTEXT:\n" + "\n\n".join(context_blocks)
        
        try:
            response = await llm_client.complete(system=cls.SYSTEM_PROMPT, user=user_prompt)
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            result_json = json.loads(content)
            
            return SynthesisResult(
                answer=result_json.get("answer", ""),
                citations=result_json.get("citations", []),
                source_breakdown=source_counts,
                llm_used=response.llm_used
            )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return SynthesisResult(
                answer="Sorry, I encountered an error while synthesizing the answer.",
                citations=[],
                source_breakdown=source_counts,
                llm_used="error"
            )
