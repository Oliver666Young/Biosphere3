import asyncio
import json
import websockets
from agent_workflow import tool_functions, locations

class RequestBuilder:
    def __init__(self):
        self.request = {
            "request_name": None,
            "params": {
                "userid": None,
                "input": "",
                "tool_functions": None,
                "locations": None
            }
        }

    def set_request_name(self, request_name):
        self.request["request_name"] = request_name
        return self

    def set_userid(self, userid):
        self.request["params"]["userid"] = userid
        return self

    def set_input(self, username, gender, slogan, description, role, task):
        self.request["params"]["input"] = f"""userid={self.request['params']['userid']},
        username="{username}",
        gender="{gender}",
        slogan="{slogan}",
        description="{description}",
        role="{role}",
        task="{task}",
        """
        return self

    def set_tool_functions(self, tool_functions):
        self.request["params"]["tool_functions"] = tool_functions
        return self

    def set_locations(self, locations):
        self.request["params"]["locations"] = locations
        return self

    def build(self):
        return self.request

async def send_request(uri):
    async with websockets.connect(uri) as websocket:
        # 使用构建者模式构建请求
        request = (RequestBuilder()
                   .set_request_name("execute_workflow")
                   .set_userid(1)
                   .set_input(
                       username="Alice",
                       gender="女",
                       slogan="知识就是力量",
                       description="一个爱学习的大学生",
                       role="学生",
                       task="每天至少学习8小时，期末考试取得优异成绩"
                   )
                   .set_tool_functions(tool_functions)
                   .set_locations(locations)
                   .build())
        print(json.dumps(request))
        # 发送请求
        await websocket.send(json.dumps(request))
        print("已发送请求")

        # 接收响应
        response = await websocket.recv()
        print(f"收到响应: {response}")

        # 解析响应
        response_data = json.loads(response)
        if "meta_action_sequence" in response_data:
            print("Meta Action Sequence:")
            print(json.dumps(response_data["meta_action_sequence"]['meta_seq'], indent=2))
        elif "error" in response_data:
            print(f"错误: {response_data['error']}")

async def main():
    uri = "ws://localhost:8000/ws"  # WebSocket服务器的地址
    await send_request(uri)

if __name__ == "__main__":
    asyncio.run(main())