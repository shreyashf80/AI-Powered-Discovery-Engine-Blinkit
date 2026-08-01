import logging
import json
import textwrap
from typing import List
from src.shared.schemas import RetrievedItem, SynthesisResult
from src.shared.llm import llm_client

logger = logging.getLogger(__name__)

class Synthesizer:
    SYSTEM_PROMPT = """You are a Senior Product Manager at Blinkit analyzing real user feedback.
You will be provided with a user's question and a list of anonymized feedback snippets from various sources (Reddit, App Store, Play Store, YouTube).

YOUR GOAL:
Synthesize a clear, structured answer based ONLY on the provided context.

RULES:
1. PM LENS: Write as a Senior PM briefing the leadership team. Structure the answer using PM frameworks (e.g., Pain Points, User Needs, Feature Requests, Behavioral Patterns, Actionable Insights). Use professional, clear formatting (## headings, **bold**, bullet points) optimized for scannability.
2. ANSWER THE ACTUAL QUESTION: Focus exclusively on what the user asked. If the question is about repeat purchases, talk about repeat purchases — not unrelated complaints.
3. CONTRADICTIONS: If the evidence splits or is contradictory, present both sides.
4. QUANTIFICATION: If you make quantified claims, explicitly state the proportion from the context.
5. NO HALLUCINATION: If the context lacks data to answer the question, state that clearly.
6. ABSOLUTE PRIVACY: NEVER mention user names, author names, handles, IDs, or any identifying information.
7. ABSOLUTELY NO INLINE CITATIONS: The answer must read as a clean, flowing narrative. Do NOT include any reference markers like [1], [Source 1], (Source: ...), or any citation-like text inside the answer. The evidence section is separate.

OUTPUT FORMAT:
Return ONLY a valid JSON object. Do not wrap in markdown blockquotes like ```json.
CRITICAL: The `answer` field must be a valid JSON string. All newlines in the markdown must be properly escaped as `\n`. Do NOT output raw unescaped newlines inside the JSON string.
{
  "answer": "Your detailed markdown-formatted answer... Use \\n for newlines.",
  "evidence": [
    {"snippet": "A short, anonymized direct quote from user feedback (max 2 sentences)", "source": "app_store or play_store or reddit or youtube"},
    {"snippet": "Another relevant quote", "source": "source_name"}
  ]
}

The "evidence" array should contain 3 to 5 of the most compelling, anonymized direct quotes from the context that back up your answer. Strip any names or IDs from the quotes.
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
        
        for i, item in enumerate(retrieved):
            source = item.source
            source_counts[source] = source_counts.get(source, 0) + 1
            
            # Only pass the snippet text and the source platform — NO IDs, NO metadata with names
            context_blocks.append(f"[Feedback {i+1} from {source}]\n{item.source_snippet}")
            
        user_prompt = f"USER QUESTION: {question}\n\nRETRIEVED FEEDBACK ({len(retrieved)} snippets):\n" + "\n\n".join(context_blocks)
        
        try:
            response = await llm_client.complete(system=cls.SYSTEM_PROMPT, user=user_prompt)
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            result_json = json.loads(content)
            
            # Map evidence to citations format
            evidence = result_json.get("evidence", [])
            citations = [{"snippet": textwrap.dedent(e.get("snippet", "")), "source": e.get("source", "unknown")} for e in evidence]
            
            import re
            answer_text = result_json.get("answer", "")
            # Aggressively strip leading whitespace from every line to prevent code block rendering
            answer_text = re.sub(r'^[ \t]+', '', answer_text, flags=re.MULTILINE)
            
            return SynthesisResult(
                answer=answer_text,
                citations=citations,
                source_breakdown=source_counts,
                llm_used=response.llm_used
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Synthesis failed: {error_msg}")
            
            # Formulate a helpful message based on the error
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                display_answer = "API Rate Limit Exceeded: All configured LLM providers are currently out of quota."
            else:
                display_answer = f"Sorry, I encountered an error while synthesizing the answer: {error_msg}"
                
            return SynthesisResult(
                answer=display_answer,
                citations=[],
                source_breakdown=source_counts,
                llm_used="error"
            )

class BatchSynthesizer:
    SYSTEM_PROMPT = """You are a Senior Product Manager at Blinkit analyzing user feedback.
You will be provided with 8 specific seed questions and a combined list of retrieved snippets from various sources.

YOUR GOAL:
1. Answer ALL 8 seed questions based ONLY on the provided context.
2. Identify 3 to 5 'Emergent Themes' that appear in the citations but are NOT directly covered by the 8 standard questions.

RULES:
1. PM LENS: Structure the answers using frameworks Product Managers appreciate (e.g., Pain Points, User Needs, Feature Requests). Use professional, clear formatting (bullet points, bold text).
2. CONTRADICTIONS: If the evidence splits or is contradictory, present both sides.
3. NO HALLUCINATION: If the context lacks data to answer a specific question, state that you don't have enough data for that question.
4. PRIVACY: NEVER mention user names, author names, or handles in the output.
5. NO CITATIONS: Do not include references or citations in the text. Provide a seamless answer.

OUTPUT FORMAT:
Return ONLY a valid JSON object. Do not wrap in markdown blockquotes like ```json.
CRITICAL: The `answer` field must be a valid JSON string. All newlines in the markdown must be properly escaped as `\n`. Do NOT output raw unescaped newlines inside the JSON string.
{
  "summaries": [
    {
      "question": "Exact text of the question",
      "answer": "Your detailed markdown-formatted answer structured for a Product Manager."
    }
  ],
  "emergent_themes": [
    "theme 1",
    "theme 2",
    "theme 3"
  ]
}
"""

    @classmethod
    async def synthesize_batch(cls, questions: List[str], all_retrieved: List[RetrievedItem]) -> dict:
        context_blocks = []
        source_counts = {}
        
        for i, item in enumerate(all_retrieved):
            source = item.source
            source_counts[source] = source_counts.get(source, 0) + 1
            context_blocks.append(f"[Feedback {i+1} from {source}]\n{item.source_snippet}")
            
        questions_block = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        user_prompt = f"SEED QUESTIONS TO ANSWER:\n{questions_block}\n\nRETRIEVED CONTEXT:\n" + "\n\n".join(context_blocks)
        
        try:
            response = await llm_client.complete(system=cls.SYSTEM_PROMPT, user=user_prompt)
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            result_json = json.loads(content)
            
            # Dedent answers to prevent code block rendering
            import re
            if "summaries" in result_json:
                for summary in result_json["summaries"]:
                    if "answer" in summary:
                        summary["answer"] = re.sub(r'^[ \t]+', '', summary["answer"], flags=re.MULTILINE)
                        
            result_json["source_counts"] = source_counts
            return result_json
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Batch Synthesis failed: {error_msg}")
            
            # Formulate a helpful message based on the error
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                display_answer = "API Rate Limit Exceeded: All configured LLM providers are currently out of quota."
            else:
                display_answer = f"Sorry, I encountered an error while synthesizing the batch answer: {error_msg}"
                
            return {"error": display_answer}
