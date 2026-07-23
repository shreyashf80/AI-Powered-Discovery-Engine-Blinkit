import sqlite3
import re
from collections import Counter

def main():
    conn = sqlite3.connect("data/engine.db")
    cursor = conn.cursor()
    cursor.execute("SELECT source, content_type, title, body, rating FROM raw_items ORDER BY RANDOM() LIMIT 500;")
    rows = cursor.fetchall()
    
    total = len(rows)
    print(f"--- Analyzed {total} Random Items ---")
    
    under_15 = 0
    under_25 = 0
    emoji_only = 0
    career_mentions = 0
    rich_feedback = 0
    
    career_keywords = ["job", "hiring", "interview", "resume", "ctc", "salary"]
    
    short_examples = []
    emoji_examples = []
    career_examples = []
    rich_examples = []
    
    for r in rows:
        source, ctype, title, body, rating = r
        body_clean = body.strip() if body else ""
        text_only = re.sub(r'[^\w\s]', '', body_clean).strip()
        
        # Lengths
        if len(body_clean) < 15:
            under_15 += 1
            if len(short_examples) < 5: short_examples.append(body_clean)
        elif len(body_clean) < 25:
            under_25 += 1
            if len(short_examples) < 10: short_examples.append(body_clean)
            
        # Emoji only (no alphanumeric chars but has length)
        if len(body_clean) > 0 and len(text_only) == 0:
            emoji_only += 1
            if len(emoji_examples) < 5: emoji_examples.append(body_clean)
            
        # Career
        body_lower = body_clean.lower()
        if any(kw in body_lower for kw in career_keywords):
            career_mentions += 1
            if len(career_examples) < 5: career_examples.append(body_clean[:100])
            
        # Rich feedback
        if len(body_clean) > 50:
            rich_feedback += 1
            if len(rich_examples) < 5: rich_examples.append(body_clean[:100])

    print(f"1. Length < 15 chars: {under_15} ({under_15/total*100:.1f}%)")
    print(f"2. Length 15-25 chars: {under_25} ({under_25/total*100:.1f}%)")
    print(f"3. Emoji-only (no words): {emoji_only} ({emoji_only/total*100:.1f}%)")
    print(f"4. Contains Career/Job keywords: {career_mentions} ({career_mentions/total*100:.1f}%)")
    print(f"5. Rich Feedback (>50 chars): {rich_feedback} ({rich_feedback/total*100:.1f}%)")
    
    print("\n--- Examples of Short (<25) ---")
    for ex in short_examples: print(f"- {ex}")
        
    print("\n--- Examples of Emoji-only ---")
    for ex in emoji_examples: print(f"- {ex}")
        
    print("\n--- Examples of Career/Job Noise ---")
    for ex in career_examples: print(f"- {ex}")
        
    print("\n--- Examples of Rich Feedback ---")
    for ex in rich_examples: print(f"- {ex}")

if __name__ == "__main__":
    main()
