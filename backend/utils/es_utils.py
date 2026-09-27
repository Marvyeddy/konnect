from backend.external.database import es_client


async def search_entity_ids(
    index_name: str,
    search_text: str = None,
    search_fields: list[str] = None,
    filters: dict = None,
) -> list[str]:
    must_queries = []

    if search_text and search_fields:
        must_queries.append(
            {
                "multi_match": {
                    "query": search_text,
                    "fields": search_fields,
                    "fuzziness": "AUTO",
                }
            }
        )

    if filters:
        for field, value in filters.items():
            if value is not None:
                must_queries.append({"term": {field: value}})

    query = {"bool": {"must": must_queries}} if must_queries else {"match_all": {}}

    response = await es_client.search(
        index=index_name, query=query, source=["id"], size=100
    )

    return [hit["_source"]["id"] for hit in response["hits"]["hits"]]
