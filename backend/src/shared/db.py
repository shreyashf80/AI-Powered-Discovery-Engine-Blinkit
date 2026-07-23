import sqlite3
import json
import os
from typing import List
from src.shared.config import config
from src.shared.schemas import RawItem, TaggedItem, PipelineStats

def get_connection():
    # Make sure DATA_DIR exists
    if not os.path.exists(config.DATA_DIR):
        # We handle this gracefully because in some environments (like Railway) 
        # it might be an absolute path that we can't create if missing, 
        # or it might be a relative path locally.
        try:
            os.makedirs(config.DATA_DIR, exist_ok=True)
        except Exception:
            pass
            
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS raw_items (
            id TEXT PRIMARY KEY,
            source TEXT,
            source_native_id TEXT,
            query_tags TEXT,
            content_type TEXT,
            title TEXT,
            body TEXT,
            author TEXT,
            rating REAL,
            timestamp TEXT,
            url TEXT,
            parent_id TEXT,
            language_detected TEXT,
            language_original TEXT,
            ingested_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tagged_items (
            id TEXT PRIMARY KEY,
            source TEXT,
            category_mentioned TEXT,
            category_tier TEXT,
            behavior_type TEXT,
            discovery_channel TEXT,
            barrier_type TEXT,
            frustration TEXT,
            unmet_need TEXT,
            segment_signal TEXT,
            sentiment TEXT,
            source_snippet TEXT,
            body TEXT,
            timestamp TEXT,
            rating REAL,
            url TEXT,
            extraction_model TEXT,
            extracted_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS pipeline_stats (
            run_id TEXT PRIMARY KEY,
            source TEXT,
            run_timestamp TEXT,
            raw_ingested INTEGER,
            stage1_passed INTEGER,
            stage2_tagged INTEGER,
            relevant_embedded INTEGER,
            irrelevant_discarded INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS connector_states (
            source TEXT PRIMARY KEY,
            state_json TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_raw_items(items: List[RawItem]):
    conn = get_connection()
    c = conn.cursor()
    for item in items:
        query_tags_json = json.dumps(item.query_tags)
        c.execute('''
            INSERT OR REPLACE INTO raw_items 
            (id, source, source_native_id, query_tags, content_type, title, body, author, rating, timestamp, url, parent_id, language_detected, language_original, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.id, item.source, item.source_native_id, query_tags_json, item.content_type, 
            item.title, item.body, item.author, item.rating, item.timestamp, item.url, 
            item.parent_id, item.language_detected, item.language_original, item.ingested_at
        ))
    conn.commit()
    conn.close()

def insert_tagged_item(item: TaggedItem):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO tagged_items 
        (id, source, category_mentioned, category_tier, behavior_type, discovery_channel, barrier_type, frustration, unmet_need, segment_signal, sentiment, source_snippet, body, timestamp, rating, url, extraction_model, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        item.id, item.source, json.dumps(item.category_mentioned), json.dumps(item.category_tier), 
        item.behavior_type, item.discovery_channel, item.barrier_type, json.dumps(item.frustration), 
        item.unmet_need, item.segment_signal, item.sentiment, item.source_snippet, item.body, 
        item.timestamp, item.rating, item.url, item.extraction_model, item.extracted_at
    ))
    conn.commit()
    conn.close()

def insert_tagged_items(items: List[TaggedItem]):
    conn = get_connection()
    c = conn.cursor()
    for item in items:
        c.execute('''
            INSERT OR REPLACE INTO tagged_items 
            (id, source, category_mentioned, category_tier, behavior_type, discovery_channel, barrier_type, frustration, unmet_need, segment_signal, sentiment, source_snippet, body, timestamp, rating, url, extraction_model, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.id, item.source, json.dumps(item.category_mentioned), json.dumps(item.category_tier), 
            item.behavior_type, item.discovery_channel, item.barrier_type, json.dumps(item.frustration), 
            item.unmet_need, item.segment_signal, item.sentiment, item.source_snippet, item.body, 
            item.timestamp, item.rating, item.url, item.extraction_model, item.extracted_at
        ))
    conn.commit()
    conn.close()

def delete_irrelevant_raw(item_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM raw_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def insert_pipeline_stats(stats: PipelineStats):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO pipeline_stats
        (run_id, source, run_timestamp, raw_ingested, stage1_passed, stage2_tagged, relevant_embedded, irrelevant_discarded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        stats.run_id, stats.source, stats.run_timestamp, stats.raw_ingested, stats.stage1_passed,
        stats.stage2_tagged, stats.relevant_embedded, stats.irrelevant_discarded
    ))
    conn.commit()
    conn.close()

def get_pipeline_stats() -> List[PipelineStats]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM pipeline_stats ORDER BY run_timestamp DESC")
    rows = c.fetchall()
    conn.close()
    
    stats_list = []
    for r in rows:
        stats_list.append(PipelineStats(
            run_id=r['run_id'],
            source=r['source'],
            run_timestamp=r['run_timestamp'],
            raw_ingested=r['raw_ingested'],
            stage1_passed=r['stage1_passed'],
            stage2_tagged=r['stage2_tagged'],
            relevant_embedded=r['relevant_embedded'],
            irrelevant_discarded=r['irrelevant_discarded']
        ))
    return stats_list

def get_tagged_items_count() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tagged_items")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_connector_state(source: str) -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT state_json FROM connector_states WHERE source = ?", (source,))
    row = c.fetchone()
    conn.close()
    if row and row['state_json']:
        return json.loads(row['state_json'])
    return {}

def save_connector_state(source: str, state: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO connector_states (source, state_json)
        VALUES (?, ?)
    ''', (source, json.dumps(state)))
    conn.commit()
    conn.close()

def is_item_ingested(item_id: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM raw_items WHERE id = ?", (item_id,))
    row = c.fetchone()
    conn.close()
    return bool(row)
