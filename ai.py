import asyncio
import websockets
import json
import os
import ssl
from datetime import datetime
from collections import defaultdict
from graph_instance import LangGraphInstance
from loguru import logger
from llm_tools.single_command_generator import CommandGenerator
from llm_tools.action_list_generator import ActionListGenerator

# websocket连接->agent_instance
character_objects = {}

# 使用 defaultdict 初始化 action_results
action_results = defaultdict(list)


async def handler(websocket, path):
    try:
        success, response = await initialize_connection(websocket)
        await websocket.send(json.dumps(response))
        if not success:
            logger.error(f"🔗 Connection failed from {websocket.remote_address}❌")
            return
        logger.info(f"🔗 Connection from {websocket.remote_address}✅")
        await character_objects[websocket.remote_address].task
    except websockets.ConnectionClosed:
        logger.error(f"🔗 Connection closed from {websocket.remote_address}❌")
    finally:
        if websocket.remote_address in character_objects:
            persist_data(websocket.remote_address)
            del character_objects[websocket.remote_address]


async def initialize_connection(websocket):
    init_message = await websocket.recv()
    init_data = json.loads(init_message)
    character_id = init_data.get("characterId")
    message_name = init_data.get("messageName")
    message_code = init_data.get("messageCode")
    websocket_address = websocket.remote_address

    if not character_id:
        return False, create_message(
            character_id,
            message_name,
            message_code,
            **{"result": False, "msg": "character init failed"},
        )

    if websocket_address in character_objects:
        return False, create_message(
            character_id,
            message_name,
            message_code,
            **{"result": False, "msg": "websocket address is already in use"},
        )

    if character_id in [agent.character_id for agent in character_objects.values()]:
        return False, create_message(
            character_id,
            message_name,
            message_code,
            **{"result": False, "msg": "character ID is already in use"},
        )

    # 这时初始化一个agent实例
    agent_instance = LangGraphInstance(character_id, websocket)
    character_objects[websocket_address] = agent_instance

    return True, create_message(
        character_id,
        message_name,
        message_code,
        **{"result": True, "msg": "character init success"},
    )


# # 根据消息类型处理消息并生成响应
# async def process_request(message, websocket_address):
#     message_name = message.get("messageName")
#     character_id = message.get("characterId")
#     message_code = message.get("messageCode")
#     data = message.get("data")
#     response = {
#         "characterId": character_id,
#         "messageCode": message_code,
#         "messageName": message_name,
#         "data": {},
#     }

#     # 连接初始化
#     if message_name == "connectionInit":
#         data = await add_websocket_connection(websocket_address, character_id)
#         response["data"] = data
#     # 动作结果
#     elif message_name == "actionresult":
#         data = await record_action_result(data, websocket_address)
#         response["data"] = data
#     # 还有其他的游戏事件待补充
#     else:
#         data = {"result": False, "msg": "Unknown message type."}
#         response["data"] = data

#     return response


"""
处理websocket request并返回对应response的函数
"""


# async def add_websocket_connection(websocket_address, character_id):
#     if not character_id:
#         return {"result": False, "msg": "character init failed"}
#     if character_id in character_objects.values():
#         return {"result": False, "msg": "character ID is already in use"}
#     if websocket_address in character_objects:
#         return {"result": False, "msg": "websocket address is already in use"}

#     print(f"Connection from {websocket_address} and character_id: {character_id}")
#     return {"result": True, "msg": "character init success"}


# async def record_action_result(data, websocket_address):
#     try:
#         character_id = character_objects.get(websocket_address)
#         if character_id:
#             action_results[character_id].append(data)
#             return {"result": True, "msg": "action result recorded"}
#         else:
#             return {"result": False, "msg": "character ID not found"}
#     except Exception as e:
#         return {"result": False, "msg": f"An error occurred: {str(e)}"}


"""
定时任务
"""


# 监听游戏端发送的消息：actionresult、gameevent等
# async def receive_messages(websocket):
#     try:
#         async for message in websocket:
#             print(f"Received message from game endpoint: {message}")
#             response = await process_request(json.loads(message), websocket.remote_address)
#             await websocket.send(json.dumps(response))
#     except websockets.ConnectionClosed:
#         print("Connection closed while receiving messages.")


# async def receive_messages(websocket, user_agent):
#     try:
#         async for message in websocket:
#             print(f"Received message from game endpoint: {message}")
#             data = json.loads(message)
#             # 将消息交给agent处理
#             await user_agent.handle_message(data)
#     except websockets.ConnectionClosed:
#         print("Connection closed while receiving messages.")


# 每隔一段时间发送一个action List消息
# async def send_scheduled_messages(client, character_id):
#     while True:
#         character_profile = "The character is energetic, and the goal is to earn as much money as possible."
#         memory = "The character has recently caught 10 fish and picked 10 apples."
#         status = "Energy: 100, Health:100, Money: 20, Hungry: 100, Study XP: 0, Education Level: PrimarySchool"
#         action_list_generator = ActionListGenerator()
#         action_list = action_list_generator.generate_action_list(
#             character_profile, memory, status
#         )
#         print(action_list)
#         message = create_message(character_id, "actionList", 6, command=action_list)
#         await client.send(json.dumps(message))
#         await asyncio.sleep(3600)


# 生成一个任务表，解析成多个排列好的单个任务，交给scheduler规划
# async def schedule_tasks(scheduler):
#     task_list = [
#         "去果园",
#         "摘10个苹果",
#         "去矿场",
#         "挖3个铁矿",
#         "去鱼塘",
#         "钓8条鱼",
#         "看看自己的所有物品",
#         "卖掉5个苹果",
#         "卖掉3个铁矿",
#         "卖掉8条鱼",
#         "回家",
#         "睡10小时",
#     ]
#     # 引入command generator
#     command_generator = CommandGenerator()
#     task_commands = []
#     for task in task_list:
#         command = command_generator.generate_single_command_body(
#             task, scheduler.character_id
#         )
#         task_commands.append(command)
#     print(task_commands)
#     # await scheduler.schedule_task(task)


"""
辅助函数
"""


# 创建消息的辅助函数
def create_message(character_id, message_name, message_code, **kwargs):
    return {
        "characterId": character_id,
        "messageCode": message_code,
        "messageName": message_name,
        "data": kwargs,
    }


# 删除websocket连接并保存action_results数据
# def delete_websocket_connection(websocket_address):
#     if websocket_address in character_objects:
#         persist_data(websocket_address)
#         del character_objects[websocket_address]


# 保存action_results数据
def persist_data(websocket_address):
    character_id = character_objects[websocket_address].character_id
    if character_id and character_id in action_results:
        # 确保目录存在
        directory = "action_results"
        if not os.path.exists(directory):
            os.makedirs(directory)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{directory}/{character_id}_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(action_results[character_id], f, indent=4)
        logger.info(f"📁 Data for {character_id} saved to {filename}")
        # 清除已保存的数据
        del action_results[character_id]


async def main():
    # ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # ssl_context.load_cert_chain(
    #     certfile="/etc/ssl/certs/bio3.crt", keyfile="/etc/ssl/certs/bio3.key"
    # )
    host = "0.0.0.0"
    port = 8097
    server = await websockets.serve(
        handler,
        host,
        port,
        # ssl=ssl_context
    )
    logger.info(f"🔗 WebSocket server started at ws://{host}:{port}")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
