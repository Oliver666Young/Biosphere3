from langchain.tools import Tool
import requests

BASE_URL = "http://localhost:8000"

def create_api_tool(endpoint, name, description):
    def api_call(**kwargs):
        response = requests.post(f"{BASE_URL}{endpoint}", json=kwargs)
        return response.json()
    
    tool = Tool(
        name=name,
        func=api_call,
        description=description
    )
    return tool

# 封装各个API端点
trade_tool = create_api_tool(
    "/trade",
    "Trade",
    "Execute a trade. Parameters: merchantid (int), merchantnum (int), transactiontype (int, 0 or 1)"
)

work_change_tool = create_api_tool(
    "/work-change",
    "Change Job",
    "Change a character's job. Parameters: jobid (int)"
)

resume_submission_tool = create_api_tool(
    "/resume-submission",
    "Submit Resume",
    "Submit a resume for a job. Parameters: jobid (int), cvurl (str)"
)

vote_tool = create_api_tool(
    "/vote",
    "Vote",
    "Submit a vote. Parameters: userid (str)"
)

public_job_tool = create_api_tool(
    "/public-job",
    "Public Job",
    "Execute a public job. Parameters: jobid (int), timelength (int)"
)

study_tool = create_api_tool(
    "/study",
    "Study",
    "Study for a certain amount of time. Parameters: timelength (int)"
)

talk_tool = create_api_tool(
    "/talk",
    "Talk",
    "Start or continue a conversation. Parameters: userid (str), talkcontent (str), talkid (str, optional)"
)

end_talk_tool = create_api_tool(
    "/end-talk",
    "End Talk",
    "End a conversation. Parameters: userid (str), talkid (str)"
)

go_to_tool = create_api_tool(
    "/go-to",
    "Go To",
    "Move to a new location. Parameters: to (str)"
)

freelance_job_tool = create_api_tool(
    "/freelance-job",
    "Freelance Job",
    "Execute a freelance job. Parameters: timelength (int), merchantid (str, optional)"
)

use_tool = create_api_tool(
    "/use",
    "Use Item",
    "Use an item. Parameters: merchantid (int), merchantnum (int, optional)"
)

see_doctor_tool = create_api_tool(
    "/see-doctor",
    "See Doctor",
    "Visit a doctor. No parameters required."
)

sleep_tool = create_api_tool(
    "/sleep",
    "Sleep",
    "Sleep for a certain amount of time. Parameters: timelength (int)"
)

# 将所有工具整合到一个列表中
all_tools = [
    trade_tool,
    work_change_tool,
    resume_submission_tool,
    vote_tool,
    public_job_tool,
    study_tool,
    talk_tool,
    end_talk_tool,
    go_to_tool,
    freelance_job_tool,
    use_tool,
    see_doctor_tool,
    sleep_tool,
]

if __name__ == "__main__":
    from langchain.agents import create_react_agent
    from langchain_openai import OpenAI
    from langchain_core.prompts import PromptTemplate
    # from llm_tools import GPTCaller

    template = '''Answer the following questions as best you can. You have access to the following tools:

    {tools}

    Use the following format:

    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question
    
    Begin!

    Question: {input}
    Thought:{agent_scratchpad}
    '''

    prompt = PromptTemplate.from_template(template)
    # llm = GPTCaller(model="gpt-4o-mini", base_url="https://api.aiproxy.io/v1/chat/completions")

    llm = OpenAI(
        temperature=0, 
        model="Qwen/Qwen2-72B-Instruct-GPTQ-Int8",
        base_url="http://143.89.16.145:5009/v1",
        api_key="EMPTY"
    )

    agent = create_react_agent(
        tools=all_tools, 
        llm=llm,
        prompt=prompt
    )

    # 使用agent
    result = agent.invoke({
        "input": "Change the job of a character to job ID 5",
        "intermediate_steps": []
    })
    print(result)