import asyncio
from backend.external.database import es_client

INDEX_SCHEMAS = {
    "products": {
        "properties": {
            "id": {"type": "keyword"},
            "vendor_id": {"type": "keyword"},
            "name": {"type": "text", "analyzer": "standard"},
            "description": {"type": "text", "analyzer": "standard"},
            "category": {"type": "keyword"},
        }
    }
}


async def init_indices():
    for index_name, mappings in INDEX_SCHEMAS.items():
        if await es_client.indices.exists(index=index_name):
            continue
        await es_client.indices.create(index=index_name, mappings=mappings)
        print(f"Created Elasticsearch index: {index_name}")


if __name__ == "__main__":
    asyncio.run(init_indices())
