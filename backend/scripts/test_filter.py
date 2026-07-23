import sqlite3
from src.shared.schemas import RawItem
from src.pipeline.relevance_filter import RelevanceFilter

def main():
    conn = sqlite3.connect("data/engine.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, source, source_native_id, query_tags, content_type, title, body, author, rating, timestamp, url, parent_id, language_detected, language_original, ingested_at FROM raw_items")
    rows = cursor.fetchall()
    
    items = []
    for r in rows:
        tags = []
        if r[3]: tags = r[3].split(",")
        item = RawItem(
            id=r[0], source=r[1], source_native_id=r[2], query_tags=tags, content_type=r[4],
            title=r[5], body=r[6], author=r[7], rating=r[8], timestamp=r[9],
            url=r[10], parent_id=r[11], language_detected=r[12], language_original=r[13], ingested_at=r[14]
        )
        items.append(item)
        
    survivors, discard_count = RelevanceFilter.apply_stage1_filter(items)
    
    print(f"Total Initial Items: {len(items)}")
    print(f"Survivors: {len(survivors)}")
    print(f"Discarded: {discard_count} ({discard_count/len(items)*100:.1f}%)")
    
if __name__ == "__main__":
    main()
