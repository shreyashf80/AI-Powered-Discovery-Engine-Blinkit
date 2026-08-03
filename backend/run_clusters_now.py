import asyncio
import json
from src.insights.cluster import generate_cluster_themes
from src.shared.db import save_cached_themes, init_db

async def main():
    print("Initializing Database...")
    init_db()
    print("Starting ML clustering on existing data...")
    themes_data = await generate_cluster_themes()
    if themes_data:
        save_cached_themes("manual_run", json.dumps(themes_data))
        print(f"Successfully generated and cached {len(themes_data)} themes!")
    else:
        print("Failed to generate themes or no data available.")

if __name__ == "__main__":
    asyncio.run(main())
