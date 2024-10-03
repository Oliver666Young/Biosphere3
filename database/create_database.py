from load_dataset import load_and_prepare_data
from create_vector_embeddings import embed_dataframe
from save_to_atlas import save_to_mongo
from create_vector_index import create_vector_search_index
from mongo_utils import connect_to_mongo
import config
import time


class DatabaseSetupApp:
    def __init__(self):
        # Initialize the database connection
        self.db = connect_to_mongo(
            db_name=config.db_name,
            mongo_uri=config.mongo_uri,
        )
        self.collections = []

    def delete_and_create_collection(self, collection_name, validator):
        # Delete existing collection if it exists
        collection = self.db[collection_name]
        if collection_name in self.db.list_collection_names():
            collection.drop()
            print(f"Collection '{collection_name}' deleted.")

        # Create new collection with validator
        self.db.create_collection(collection_name, validator=validator)
        print(f"Collection '{collection_name}' created with validator.")
        return self.db[collection_name]

    def load_and_prepare_data(self, file_name):
        # Load and prepare data from a JSON file
        df = load_and_prepare_data(file_name)
        print(f"Data from '{file_name}' loaded and prepared.")
        return df

    def create_and_save_embeddings(
        self, df, text_column, collection_name, create_index=False
    ):
        # Create embeddings
        df = embed_dataframe(
            df,
            text_column,
            config.model_name,
            config.base_url,
            config.api_key,
        )
        print(f"Embeddings created for collection '{collection_name}'.")

        # Save embeddings to MongoDB Atlas
        save_to_mongo(df, config.db_name, collection_name, config.mongo_uri)
        print(f"Data saved to MongoDB Atlas for collection '{collection_name}'.")

        # Create vector search index if needed
        if create_index:
            self.create_vector_search_index(collection_name)

    def create_vector_search_index(self, collection_name):
        # Create vector search index
        create_vector_search_index(
            config.db_name,
            collection_name,
            config.mongo_uri,
            config.index_name,
            config.num_dimensions,
            config.similarity,
        )
        collection = self.db[collection_name]

        # Wait until the index is ready
        while True:
            cursor = collection.list_search_indexes()
            index_info = list(cursor)[0]

            if index_info["status"] == "READY":
                print(
                    f"Vector search index is ready for collection '{collection_name}'."
                )
                break
            else:
                print(
                    f"Vector search index is not ready for collection '{collection_name}'. Waiting..."
                )
                time.sleep(5)

    def setup_database_with_data(
        self,
        collection_name,
        validator,
        data_file,
        text_column=None,
        create_embeddings=False,
        create_index=False,
    ):
        # Load and prepare data
        df = self.load_and_prepare_data(data_file)
        print(df.head())

        if create_embeddings and text_column:
            # Create embeddings and save data
            self.create_and_save_embeddings(
                df, text_column, collection_name, create_index
            )
        else:
            # Save data without embeddings
            save_to_mongo(df, config.db_name, collection_name, config.mongo_uri)
            print(f"Data saved to MongoDB Atlas for collection '{collection_name}'.")

    def setup_cv_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["jobid", "userid", "username", "CV_content", "created_at"],
                "properties": {
                    "jobid": {
                        "bsonType": "int",
                        "description": "工作ID,必须为整数且为必填项",
                    },
                    "userid": {
                        "bsonType": "int",
                        "description": "用户ID,必须为整数且为必填项",
                    },
                    "username": {
                        "bsonType": "string",
                        "description": "用户名,必须为字符串且为必填项",
                    },
                    "CV_content": {
                        "bsonType": "string",
                        "description": "简历内容,必须为字符串且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "创建时间,必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.cv_collection_name, validator)
        self.setup_database_with_data(
            config.cv_collection_name,
            validator,
            "CV.json",
        )

    def setup_npc_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "userid",
                    "username",
                    "gender",
                    "slogan",
                    "description",
                    "stats",
                    "role",
                    "task",
                    "created_at",
                ],
                "properties": {
                    "userid": {
                        "bsonType": "int",
                        "description": "NPC ID,必须为整数且为必填项",
                    },
                    "username": {
                        "bsonType": "string",
                        "description": "NPC 名字,必须为字符串且为必填项",
                    },
                    "gender": {
                        "bsonType": "string",
                        "description": "NPC 性别,必须为字符串且为必填项",
                    },
                    "slogan": {
                        "bsonType": "string",
                        "description": "NPC 标语,必须为字符串且为必填项",
                    },
                    "description": {
                        "bsonType": "string",
                        "description": "NPC 描述,必须为字符串且为必填项",
                    },
                    "stats": {
                        "bsonType": "object",
                        "required": [
                            "health",
                            "fullness",
                            "energy",
                            "knowledge",
                            "cash",
                        ],
                        "properties": {
                            "health": {"bsonType": "double"},
                            "fullness": {"bsonType": "double"},
                            "energy": {"bsonType": "double"},
                            "knowledge": {"bsonType": "double"},
                            "cash": {"bsonType": "double"},
                        },
                    },
                    "role": {
                        "bsonType": "string",
                        "description": "NPC 角色,必须为字符串且为必填项",
                    },
                    "task": {
                        "bsonType": "string",
                        "description": "NPC 任务,必须为字符串且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "创建时间,必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.npc_collection_name, validator)
        self.setup_database_with_data(
            config.npc_collection_name,
            validator,
            "NPC.json",
        )

    def setup_action_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "userid",
                    "created_at",
                    "meta_action",
                    "description",
                    "response",
                    "action_id",
                ],
                "properties": {
                    "userid": {
                        "bsonType": "int",
                        "description": "NPC ID,必须为整数且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "时间戳,必须为字符串且为必填项",
                    },
                    "meta_action": {
                        "bsonType": "string",
                        "description": "当前做的动作,必须为字符串且为必填项",
                    },
                    "description": {
                        "bsonType": "string",
                        "description": "大语言模型返回的结果,必须为字符串且为必填项",
                    },
                    "response": {
                        "bsonType": "bool",
                        "description": "执行是否成功,必须为布尔类型且为必填项",
                    },
                    "action_id": {
                        "bsonType": "int",
                        "description": "唯一的动作ID,必须为整数且为必填项",
                    },
                    "prev_action": {
                        "bsonType": "int",
                        "description": "前一个动作的action_id,必须为整数且为可选项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.action_collection_name, validator)

    def setup_impression_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["from_id", "to_id", "impression", "created_at"],
                "properties": {
                    "from_id": {
                        "bsonType": "int",
                        "description": "表示印象来源的 NPC 的 ID, 必须为整数且为必填项",
                    },
                    "to_id": {
                        "bsonType": "int",
                        "description": "表示印象指向的 NPC 的 ID, 必须为整数且为必填项",
                    },
                    "impression": {
                        "bsonType": "string",
                        "description": "印象内容, 必须为字符串且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "时间戳, 必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.impression_collection_name, validator)

    def setup_descriptor_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["failed_action", "action_id", "userid", "reflection"],
                "properties": {
                    "failed_action": {
                        "bsonType": "string",
                        "description": "执行失败的动作,必须为字符串且为必填项",
                    },
                    "action_id": {
                        "bsonType": "int",
                        "description": "失败动作的ID,必须为整数且为必填项",
                    },
                    "userid": {
                        "bsonType": "int",
                        "description": "NPC ID,必须为整数且为必填项",
                    },
                    "reflection": {
                        "bsonType": "string",
                        "description": "动作失败后的反思,必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.descriptor_collection_name, validator)

    def setup_daily_objective_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["userid", "created_at", "objectives"],
                "properties": {
                    "userid": {
                        "bsonType": "int",
                        "description": "用户ID，必须为整数且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "创建日期，必须为字符串且为必填项，格式为 'YYYY-MM-DD HH:MM:SS'",
                    },
                    "objectives": {
                        "bsonType": "array",
                        "description": "每日目标列表，必须为字符串数组且为必填项",
                        "items": {
                            "bsonType": "string",
                            "description": "目标内容，必须为字符串",
                        },
                    },
                },
            }
        }
        self.delete_and_create_collection(
            config.daily_objective_collection_name, validator
        )

    def setup_plan_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["userid", "created_at", "detailed_plan"],
                "properties": {
                    "userid": {
                        "bsonType": "int",
                        "description": "用户ID，必须为整数且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "创建日期，必须为字符串且为必填项，格式为 'YYYY-MM-DD HH:MM:SS'",
                    },
                    "detailed_plan": {
                        "bsonType": "string",
                        "description": "详细计划，必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.plan_collection_name, validator)

    def setup_meta_seq_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["userid", "created_at", "meta_sequence"],
                "properties": {
                    "userid": {
                        "bsonType": "int",
                        "description": "用户ID，必须为整数且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "创建日期，必须为字符串且为必填项",
                    },
                    "meta_sequence": {
                        "bsonType": "array",
                        "description": "元动作序列，必须为字符串数组且为必填项",
                        "items": {
                            "bsonType": "string",
                            "description": "元动作，必须为字符串",
                        },
                    },
                },
            }
        }
        self.delete_and_create_collection(config.meta_seq_collection_name, validator)

    def setup_diary_database(self):
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["userid", "diary_content", "created_at"],
                "properties": {
                    "userid": {
                        "bsonType": "int",
                        "description": "用户ID,必须为整数且为必填项",
                    },
                    "diary_content": {
                        "bsonType": "string",
                        "description": "日记内容,必须为字符串且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "创建时间,必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.diary_collection_name, validator)

    def drop_indexes(self, collection_name):
        collection = self.db[collection_name]
        collection.drop_indexes()
        print(f"Indexes dropped for collection '{collection_name}'.")

        try:
            collection.drop_search_index(config.index_name)
            while list(collection.list_search_indexes()):
                print(
                    f"Atlas is deleting the index for collection '{collection_name}'. Waiting..."
                )
                time.sleep(5)
            print(f"Search indexes dropped for collection '{collection_name}'.")
        except Exception as e:
            print(f"Search indexes do not exist for collection '{collection_name}'.")

    def setup_tool_database(self):
        # Drop indexes and collection
        self.drop_indexes(config.tool_collection_name)

        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["API", "text", "code"],
                "properties": {
                    "API": {
                        "bsonType": "string",
                        "description": "API的名称，必须为字符串且为必填项",
                    },
                    "text": {
                        "bsonType": "string",
                        "description": "工具的描述文本，必须为字符串且为必填项",
                    },
                    "code": {
                        "bsonType": "string",
                        "description": "工具的代码段，必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(config.tool_collection_name, validator)
        self.setup_database_with_data(
            config.tool_collection_name,
            validator,
            "API.json",
            text_column="text",
            create_embeddings=True,
            create_index=True,
        )

    def setup_conversation_database(self):
        # Drop indexes and collection
        self.drop_indexes(config.conversation_collection_name)

        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["npc_ids", "dialogue", "created_at"],
                "properties": {
                    "npc_ids": {
                        "bsonType": "array",
                        "description": "包含参与对话的NPC ID的数组，必须为整数数组且为必填项",
                        "items": {
                            "bsonType": "int",
                            "description": "NPC的ID，必须为整数",
                        },
                    },
                    "dialogue": {
                        "bsonType": "string",
                        "description": "对话内容，必须为字符串且为必填项",
                    },
                    "created_at": {
                        "bsonType": "string",
                        "description": "创建时间，必须为字符串且为必填项",
                    },
                },
            }
        }
        self.delete_and_create_collection(
            config.conversation_collection_name, validator
        )
        self.setup_database_with_data(
            config.conversation_collection_name,
            validator,
            "CONVERSATION.json",
            text_column="dialogue",
            create_embeddings=True,
            create_index=True,
        )


if __name__ == "__main__":
    app = DatabaseSetupApp()
    # app.setup_cv_database()
    # app.setup_npc_database()
    # app.setup_action_database()
    # app.setup_impression_database()
    # app.setup_descriptor_database()
    # app.setup_tool_database()
    # app.setup_daily_objective_database()
    # app.setup_plan_database()
    # app.setup_meta_seq_database()
    app.setup_conversation_database()
    # app.setup_diary_database()
