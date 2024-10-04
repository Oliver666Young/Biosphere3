from vector_search import vector_search
import config


class VectorSearchApp:
    def perform_vector_search(self, query_text, fields_to_return, collection_name):
        print(
            f"Performing vector search for query: '{query_text}' in collection: '{collection_name}'"
        )

        # Pass collection_name and fields_to_return to vector_search
        results = vector_search(
            config.db_name,
            collection_name,  # Dynamic collection name
            config.mongo_uri,
            query_text,
            config.index_name,
            config.limit,
            config.model_name,
            config.base_url,
            config.api_key,
            fields_to_return,  # Pass fields to return
        )

        # Print results
        for result in results:
            print(result)


if __name__ == "__main__":
    app = VectorSearchApp()
    app.perform_vector_search("我要换工作", ["code"], config.tool_collection_name)
    app.perform_vector_search(
        "生活习惯", ["npc_ids", "dialogue"], config.conversation_collection_name
    )
