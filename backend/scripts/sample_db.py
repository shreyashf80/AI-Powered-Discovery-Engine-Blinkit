import sqlite3
import random

def main():
    conn = sqlite3.connect("data/engine.db")
    cursor = conn.cursor()
    cursor.execute("SELECT source, content_type, title, body, rating FROM raw_items ORDER BY RANDOM() LIMIT 20;")
    rows = cursor.fetchall()
    
    print(f"Sampled {len(rows)} items:")
    for r in rows:
        source, ctype, title, body, rating = r
        print(f"[{source.upper()}] Rating: {rating}")
        if title:
            print(f"Title: {title}")
        print(f"Body: {body[:200].replace(chr(10), ' ')}")
        print("-" * 50)
        
if __name__ == "__main__":
    main()
