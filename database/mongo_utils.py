import datetime
from pymongo import MongoClient, DESCENDING
import sys
import os
from pprint import pprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import config
from database.create_vector_embeddings import embed_text

# 定义需要进行嵌入的集合及其对应的文本字段
RAG_COLLECTIONS = {
    config.tool_collection_name: "text",
    config.conversation_collection_name: "dialogue",
    # 可以在此添加更多需要嵌入的集合和对应的字段
}


def connect_to_mongo(db_name, mongo_uri):
    client = MongoClient(mongo_uri)
    db = client[db_name]
    return db


def print_collection(collection_name):
    # Connect to the MongoDB collection
    db = connect_to_mongo(
        db_name=config.db_name,
        mongo_uri=config.mongo_uri,
    )
    collection = db[collection_name]

    # Find all documents in the collection
    documents = collection.find()

    # Print each document
    for document in documents:
        pprint(document)
        print()  # Print an empty line for separation


# Create (Insert)
def insert_document(collection_name, document):
    db = connect_to_mongo(db_name=config.db_name, mongo_uri=config.mongo_uri)
    collection = db[collection_name]

    # 检查集合是否需要进行嵌入
    if collection_name in RAG_COLLECTIONS:
        field_to_embed = RAG_COLLECTIONS[collection_name]
        if field_to_embed in document:
            text = document[field_to_embed]
            # 生成嵌入向量
            embedding = embed_text(
                text,
                config.model_name,
                config.base_url,
                config.api_key,
            )
            # 添加嵌入向量到文档
            document["text_embedding"] = embedding
            print(f"Embedding added to document for collection '{collection_name}'.")
        else:
            print(f"Field '{field_to_embed}' not found in document for embedding.")

    result = collection.insert_one(document)
    return result.inserted_id


# Update
def update_documents(collection_name, query, update, upsert=False, multi=False):
    db = connect_to_mongo(
        db_name=config.db_name,
        mongo_uri=config.mongo_uri,
    )
    collection = db[collection_name]
    if multi:
        result = collection.update_many(query, update, upsert=upsert)
    else:
        result = collection.update_one(query, update, upsert=upsert)
    return result.modified_count
    # # Update a single NPC's health
    # update_documents(
    #     collection_name='npc',
    #     query={'userid': 1},
    #     update={'$set': {'stats.health': 95.0}}
    # )

    # # Update multiple NPCs to increase knowledge
    # update_documents(
    #     collection_name='npc',
    #     query={'stats.knowledge': {'$lt': 50}},
    #     update={'$inc': {'stats.knowledge': 5}},
    #     multi=True
    # )


# Delete
def delete_document(collection_name, query):
    db = connect_to_mongo(db_name=config.db_name, mongo_uri=config.mongo_uri)
    collection = db[collection_name]
    result = collection.delete_one(query)
    return result.deleted_count
    # # Delete a single NPC
    # delete_document(
    #     collection_name='npc',
    #     query={'userid': 1}
    # )


def delete_documents(collection_name, query):
    db = connect_to_mongo(db_name=config.db_name, mongo_uri=config.mongo_uri)
    collection = db[collection_name]
    result = collection.delete_many(query)
    return result.deleted_count
    # # Delete all NPCs with zero health
    # delete_documents(
    #     collection_name='npc',
    #     query={'stats.health': 0}
    # )


# Read (Query)
def find_documents(collection_name, query={}, projection=None, limit=0, sort=None):
    db = connect_to_mongo(db_name=config.db_name, mongo_uri=config.mongo_uri)
    collection = db[collection_name]
    cursor = collection.find(query, projection)
    if sort:
        cursor = cursor.sort(sort)
    if limit > 0:
        cursor = cursor.limit(limit)
    return list(cursor)
    # # Find all NPCs with health greater than 50
    # npc_docs = find_documents(
    #     collection_name='npc',
    #     query={'stats.health': {'$gt': 50}},
    #     projection={'_id': 0}, # 在查询结果中排除 _id 字段。
    #     limit=10,
    #     sort=[('created_at', DESCENDING)]
    # )


def get_latest_k_documents(collection_name, user_id, k, item):
    documents = find_documents(
        collection_name=collection_name,
        query={"userid": user_id},
        projection={item: 1, "_id": 0},
        limit=k,
        sort=[("created_at", DESCENDING)],
    )
    # return the json format
    return [doc[item] for doc in documents]


def get_impression_from_mongo(collection_name, from_id, to_id, k):
    # Connect to the MongoDB collection
    db = connect_to_mongo(db_name=config.db_name, mongo_uri=config.mongo_uri)
    collection = db[collection_name]

    # Query to find the latest k impressions with the specified from_id and to_id
    documents = find_documents(
        collection_name=collection_name,
        query={"from_id": from_id, "to_id": to_id},
        projection={"impression": 1, "_id": 0},
        limit=k,
        sort=[("created_at", DESCENDING)],
    )

    # Return only the 'impression' field from each document
    return [doc["impression"] for doc in documents]


# 获取本周所有申请人
def get_candidates_from_mongo():
    # Connect to the MongoDB collection
    db = connect_to_mongo(
        db_name=config.db_name,
        mongo_uri=config.mongo_uri,
    )
    collection = db[config.cv_collection_name]

    # Calculate the date one week ago from now
    one_week_ago = datetime.datetime.now() - datetime.timedelta(days=7)

    # Query to find candidates created within the last week
    candidates = list(
        collection.find(
            {"created_at": {"$gte": one_week_ago.strftime("%Y-%m-%d %H:%M:%S")}},
            {"_id": 0, "jobid": 1, "username": 1, "userid": 1},
        )
    )
    return candidates


def get_conversations_with_npc_ids(npc_ids_list):
    """
    查找包含所有指定 NPC IDs 的对话（不考虑顺序）。

    参数：
    - npc_ids_list: 包含 NPC IDs 的列表（整数）

    返回：
    - 包含所有指定 NPC IDs 的对话列表
    """
    query = {"npc_ids": {"$all": npc_ids_list}}
    documents = find_documents(
        collection_name=config.conversation_collection_name, query=query
    )
    return documents


def get_conversations_containing_npc_id(npc_id):
    """
    查找包含指定 NPC ID 的所有对话。

    参数：
    - npc_id: 要查找的 NPC ID（整数）

    返回：
    - 包含指定 NPC ID 的对话列表
    """
    query = {"npc_ids": npc_id}
    documents = find_documents(
        collection_name=config.conversation_collection_name, query=query
    )
    return documents


if __name__ == "__main__":

    # 获取候选人
    # print(get_candidates_from_mongo())

    # # 更新 npc 集合中 userid 为 0 的文档的 stats.health 字段
    # modified_count = update_document(
    #     config.npc_collection_name, {"userid": 0}, {"$set": {"stats.health": 8.5}}
    # )
    # print(f"Updated {modified_count} document(s)")
    # print_collection(config.npc_collection_name)

    # # 更新 cv 集合中 username 为 "Vitalik Buterin" 的文档的 CV_content 字段
    # modified_count = update_document(
    #     config.cv_collection_name,
    #     {"username": "Vitalik Buterin"},
    #     {"$set": {"CV_content": "Updated CV content"}},
    # )
    # print(f"Updated {modified_count} document(s)")
    # print_collection(config.cv_collection_name)

    # print(
    #     get_latest_k_documents(
    #         config.daily_objective_collection_name, 8, 2, "objectives"
    #     )
    # )

    # # Define the impressions to insert as separate documents
    # impressions = [
    #     {
    #         "from_id": 1,
    #         "to_id": 2,
    #         "impression": "Bob seems friendly and helpful.",
    #         "created_at": "2024-08-02 13:30:00",
    #     },
    #     {
    #         "from_id": 1,
    #         "to_id": 2,
    #         "impression": "Bob knows a lot about the hidden treasure.",
    #         "created_at": "2023-06-10 14:00:00",
    #     },
    # ]

    # # Insert each impression as a separate document into the 'impression' collection
    # for impression in impressions:
    #     inserted_id = insert_document("impression", impression)
    #     print(f"Inserted document with ID: {inserted_id}")

    print(get_impression_from_mongo(config.impression_collection_name, 1, 2, 2))

    # new_conversation = {
    #     "npc_ids": [4, 8],
    #     "dialogue": "David: Hey Mike, have you checked out the new gym in town?\nMike: Not yet, but I’ve heard great things about it. Do you want to go together?\nDavid: Sure! I could use a good workout after this busy week.\nMike: Let’s make it happen this weekend!",
    #     "created_at": "2024-10-05 14:00:00",
    # }

    # inserted_id = insert_document(config.conversation_collection_name, new_conversation)
    # print(f"Inserted document ID: {inserted_id}")
