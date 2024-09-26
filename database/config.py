# MongoDB Configuration
db_name = "biosphere3_test"
tool_collection_name = "api"
cv_collection_name = "cv"
npc_collection_name = "npc"
action_collection_name = "action"
impression_collection_name = "impression"
descriptor_collection_name = "descriptor"
daily_objective_collection_name = "daily_objective"
plan_collection_name = "plan"
meta_seq_collection_name = "meta_seq"
conversation_collection_name = "conversation"
mongo_uri = "mongodb+srv://bauhiniaai:nb666@biosphere3.e1px8.mongodb.net/?connectTimeoutMS=30000"
index_name = "vector_index"

# Model and API Configuration
api_key = "sk-tejMSVz1e3ziu6nB0yP2wLiaCUp2jR4Jtf4uaAoXNro6YXmh"
base_url = "https://api.aiproxy.io/v1"
model_name = "text-embedding-3-small"  # OpenAI Model
num_dimensions = 1536  # Dimensions for OpenAI model
limit = 5
similarity = "euclidean"
