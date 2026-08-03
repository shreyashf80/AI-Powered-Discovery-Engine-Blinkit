import logging
import json
import asyncio
from typing import List, Dict, Any
from src.pipeline.embedder import Embedder
from src.shared.db import get_connection
from src.shared.llm import llm_client

logger = logging.getLogger(__name__)

async def name_cluster(snippets: List[str]) -> Dict[str, str]:
    system_prompt = "You are a Senior Product Manager analyzing user feedback."
    
    prompt = "Here are 5 representative feedback snippets from users belonging to a specific cluster:\n\n"
    for i, s in enumerate(snippets):
        prompt += f"{i+1}. \"{s}\"\n"
    
    prompt += (
        "\nRead these and provide a catchy 2-5 word Theme Name and a 2-sentence description of the core issue.\n"
        "Output exactly in JSON format: {\"theme_name\": \"...\", \"theme_description\": \"...\"}\n"
        "Do NOT wrap in markdown blocks like ```json."
    )
    
    try:
        response = await llm_client.complete(system=system_prompt, user=prompt)
        text = response.content.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Failed to name cluster: {e}")
        return {"theme_name": "Uncategorized Cluster", "theme_description": "Failed to generate description due to AI error."}

async def generate_cluster_themes() -> List[Dict[str, Any]]:
    logger.info("Starting ML K-Means clustering for Discovery Themes...")
    
    # 1. Lazy load heavy ML libraries to respect Railway 500MB RAM limit
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import euclidean_distances
    
    # 2. Fetch all data from ChromaDB
    chroma = Embedder.get_chroma_client()
    try:
        collection = chroma.get_collection(name="discovery_engine")
        data = collection.get(include=["embeddings", "documents", "metadatas"])
    except Exception as e:
        logger.warning(f"Chroma collection not found or empty: {e}")
        return []
        
    if not data or not data["embeddings"]:
        logger.warning("No embeddings found in ChromaDB for clustering.")
        return []
        
    embeddings = np.array(data["embeddings"])
    ids = data["ids"]
    docs = data["documents"]
    metadatas = data["metadatas"]
    
    n = len(embeddings)
    if n < 3:
        logger.warning("Not enough data to cluster (need at least 3 items).")
        return []
        
    # 3. Dynamic K Selection: between 3 and 8 clusters based on volume
    k = max(3, min(8, n // 10))
    logger.info(f"Clustering {n} items into {k} dynamic themes...")
    
    # 4. Run K-Means Clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(embeddings)
    centroids = kmeans.cluster_centers_
    
    clusters = []
    
    # 5. Process each cluster and filter outliers
    for i in range(k):
        cluster_indices = np.where(labels == i)[0]
        if len(cluster_indices) == 0:
            continue
            
        cluster_embeddings = embeddings[cluster_indices]
        centroid = centroids[i].reshape(1, -1)
        
        # Calculate distances to centroid for noise filtering / ordering
        dists = euclidean_distances(cluster_embeddings, centroid).flatten()
        sorted_rel_indices = np.argsort(dists)
        sorted_abs_indices = cluster_indices[sorted_rel_indices]
        
        # Get the top 5 closest snippets to the mathematical center for LLM naming
        top_indices = sorted_abs_indices[:5]
        
        # Fetch metadata from SQLite to get accurate Sentiment and Source splits
        cluster_ids = [ids[idx] for idx in cluster_indices]
        
        conn = get_connection()
        c = conn.cursor()
        placeholders = ','.join(['?'] * len(cluster_ids))
        c.execute(f"SELECT sentiment, source FROM tagged_items WHERE id IN ({placeholders})", cluster_ids)
        rows = c.fetchall()
        conn.close()
        
        sentiments = [r["sentiment"] for r in rows if r["sentiment"]]
        sources = [r["source"] for r in rows if r["source"]]
        
        sentiment_split = {}
        for s in sentiments:
            sentiment_split[s] = sentiment_split.get(s, 0) + 1
            
        source_split = {}
        for s in sources:
            source_split[s] = source_split.get(s, 0) + 1
            
        # Convert to percentages
        for s in sentiment_split:
            sentiment_split[s] = round((sentiment_split[s] / len(sentiments)) * 100) if sentiments else 0
        for s in source_split:
            source_split[s] = round((source_split[s] / len(sources)) * 100) if sources else 0
            
        clusters.append({
            "volume": len(cluster_indices),
            "evidence": [{"text": docs[idx], "source": metadatas[idx].get("source", "unknown")} for idx in top_indices],
            "sentiment_split": sentiment_split,
            "source_split": source_split,
        })
        
    # 6. Name clusters via LLM in parallel
    logger.info("Naming clusters via LLM...")
    tasks = []
    for c in clusters:
        snippets_text = [e["text"] for e in c["evidence"]]
        tasks.append(name_cluster(snippets_text))
        
    names = await asyncio.gather(*tasks)
    
    # 7. Combine results
    final_themes = []
    for i, c in enumerate(clusters):
        theme_info = names[i]
        final_themes.append({
            "theme_name": theme_info.get("theme_name", f"Theme {i+1}"),
            "theme_description": theme_info.get("theme_description", ""),
            "volume": c["volume"],
            "sentiment_split": c["sentiment_split"],
            "source_split": c["source_split"],
            "evidence": c["evidence"]
        })
        
    # Sort by volume descending
    final_themes.sort(key=lambda x: x["volume"], reverse=True)
    logger.info("ML Clustering complete!")
    return final_themes
