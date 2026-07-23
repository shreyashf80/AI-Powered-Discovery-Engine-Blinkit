import asyncio
from src.connectors.app_store import AppStoreConnector
from scripts.ingest import IngestionConfig

async def main():
    connector = AppStoreConnector()
    config = IngestionConfig()
    items = await connector.fetch(config)
    print(f"Fetched {len(items)} items")
    if items:
        print("First item:", items[0].title, "-", items[0].body[:50])

if __name__ == "__main__":
    asyncio.run(main())
