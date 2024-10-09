import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from agent_workflow import app as workflow_app, PlanExecute

app = FastAPI()
SAMPLE_RESPONSE = {
    "meta_action_sequence": {
        "meta_seq": ["Nav(school)", "Nav(square)", "Nav(workshop)"]
    }
}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            # 接收客户端消息
            # data = await websocket.receive_text()
            # request = json.loads(data)
            await websocket.send_text(json.dumps(SAMPLE_RESPONSE))
            break
            # # 解析请求
            # request_name = request.get("request_name")
            # params = request.get("params", {})

            # # 执行工作流
            # if request_name == "execute_workflow":
            #     state = PlanExecute(**params)
            #     config = {"recursion_limit": 10}

            #     result = None
            #     async for event in workflow_app.astream(state, config=config):
            #         for k, v in event.items():
            #             if k == "meta_action_sequence":
            #                 result = v
            #                 break
            #         if result:
            #             break

            #     # 返回结果给客户端
            # await websocket.send_text(json.dumps({"meta_action_sequence": result}))
            # else:
            #     await websocket.send_text(json.dumps({"error": "未知的请求名称"}))

        except WebSocketDisconnect:
            print("客户端断开连接")
            break
        except Exception as e:
            await websocket.send_text(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
