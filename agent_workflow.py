import os
from langchain import hub
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import (
    do_freelance_job,
    navigate_to,
    sleep,
    study,
    get_character_stats,
    get_inventory,
    do_public_job,
    talk,
    end_talk,
    see_doctor,
)
from node_model import PlanExecute, Plan, Response, Act,DailyObjective,DetailedPlan,MetaActionSequence
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START,END
import asyncio
from typing import Literal

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-tejMSVz1e3ziu6nB0yP2wLiaCUp2jR4Jtf4uaAoXNro6YXmh"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Bio3_agent"

# 定义工具列表
tool_list = [
    do_freelance_job,
    navigate_to,
    sleep,
    study,
    get_character_stats,
    get_inventory,
    do_public_job,
    talk,
    end_talk,
    see_doctor,
]

# 创建LLM和代理
llm = ChatOpenAI(base_url="https://api.aiproxy.io/v1", model="gpt-4o-mini")
prompt = hub.pull("wfh/react-agent-executor")
agent_executor = create_react_agent(llm, tool_list, messages_modifier=prompt)

# 定义提示模板
obj_planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are the daily objectives planner in a RPG game. For the given user profile(their goals, personality, etc.), come up with a general daily objectives.
            These objectives are daily objectives that ONLY related to available actions provided.
            The final format should be a list of daily objectives. Like this:\n
            ["Working: Working in the farm","Studying: Discover something about science", "Socializing: Try to make friends"]\n
            """,
        ),
        ("placeholder", "{messages}"),
    ]
)

replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Additionally, if during the execution of a step you encounter a tool call with missing required parameters, randomly generate a reasonable parameter value to fill in, rather than throwing an error. For example, if a duration is needed but not specified, you might randomly choose a value between 1 and 8 hours.

Your objective was this:
{input}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
)

detail_planner_prompt = ChatPromptTemplate.from_template(
    """For the given daily objectives,
    \n
    {daily_objective}
    \n
    come up with a detailed plan only associated with the available actions. Suppose every day start at 8:00 AM.\n
    actions_available = [
    do_freelance_job,
    navigate_to,
    sleep,
    study,
    get_character_stats,
    get_inventory,
    do_public_job,
    talk,
    end_talk,
    see_doctor,
]\n
    The detailed plan may involve plans that are not in the daily objectives.(daily actions like eating meals, random actions like chatting with friends.)\n
    
    The final format should be a list of daily objectives. for example:\n
    [Working: "I should navigate to the farm, then do a freelance job."\n,
    daily_action:"I should eat breakfast, lunch and dinner."\n,
    Study:"I should study"\n,
    Socializing:"Perhaps I should go to the square and talk to someone."]\n
    
    """
)

meta_action_sequence_prompt = ChatPromptTemplate.from_template(
    """For the given detailed plan, think step by step to come up with a player action sequence only associated with the available actions/locations.\n
    {plan}
    \n
    
    actions_available = [
    do_freelance_job(int:hours),
    navigate_to(str:location),
    sleep(int:hours),
    study(int:hours),
    get_character_stats() -> (str:stats(health,energy)),
    get_inventory,
    do_public_job(int:hours),
    eat(int:meals),
    talk(str:to,str:message),
    end_talk,
    see_doctor,
    ]\n
    Use navigate_to to go to the location. \n
    Every day, you start at home. \n
    You need to sleep everyday.\n
    locations_available = [
    farm,
    restaurant,
    home,
    library,
    school,
    ]\n
    The final format should be a list of meta actions. for example:\n
    [navigate_to(farm),do_public_job(4),navigate_to(restaurant), eat(3), do_freelance_job(4),navigate_to(home),study(3),sleep(8)]
    \n
    """
)

meta_seq_adjuster_prompt = ChatPromptTemplate.from_template(
    """For the given meta action sequence, adjust the sequence to make sure the player can finish all the daily objectives and follow the common sense.
    For example, if you are already at the location, you don't need to navigate to it again.
    {meta_seq}
    \n
    """
)
# 创建规划器和重新规划器
obj_planner = obj_planner_prompt | ChatOpenAI(
    base_url="https://api.aiproxy.io/v1", model="gpt-4o-mini", temperature=1
).with_structured_output(DailyObjective)


# replanner = replanner_prompt | ChatOpenAI(
#     base_url="https://api.aiproxy.io/v1", model="gpt-4o-mini", temperature=0
# ).with_structured_output(Act)

detail_planner = detail_planner_prompt | ChatOpenAI(
    base_url="https://api.aiproxy.io/v1", model="gpt-4o-mini", temperature=0
).with_structured_output(DetailedPlan)

meta_action_sequence_planner = meta_action_sequence_prompt | ChatOpenAI(
    base_url="https://api.aiproxy.io/v1", model="gpt-4o-mini", temperature=0
).with_structured_output(MetaActionSequence)

meta_seq_adjuster = meta_seq_adjuster_prompt | ChatOpenAI(
    base_url="https://api.aiproxy.io/v1", model="gpt-4o-mini", temperature=0
).with_structured_output(MetaActionSequence)

# # 定义执行步骤函数
# async def execute_step(state: PlanExecute):
#     plan = state["plan"]
#     plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
#     task = plan[0]
#     task_formatted = f"""For the following plan:
# {plan_str}\n\nYou are tasked with executing step {1}, {task}."""
#     agent_response = await agent_executor.ainvoke(
#         {"messages": [("user", task_formatted)]}
#     )
#     return {"past_steps": [(task, agent_response["messages"][-1].content)]}


# async def plan_step(state: PlanExecute):
#     plan = await planner.ainvoke({"messages": [("user", state["input"])]})
#     return {"plan": plan.steps}
async def generate_daily_objective(state: PlanExecute):
    daily_objective = await obj_planner.ainvoke({"messages": [("user", state["input"])]})
    return {"daily_objective": daily_objective.objectives}

async def generate_detailed_plan(state: PlanExecute):
    detailed_plan = await detail_planner.ainvoke(state)
    with open("detailed_plan.txt", "w", encoding="utf-8") as f:
        f.write(detailed_plan.detailed_plan)
    return {"plan": detailed_plan.detailed_plan}


async def generate_meta_action_sequence(state: PlanExecute):
    meta_action_sequence = await meta_action_sequence_planner.ainvoke(state)

    with open("meta_action_sequence.txt", "w", encoding="utf-8") as f:
        f.write(str(meta_action_sequence.meta_action_sequence))
    meta_action_sequence = await meta_seq_adjuster.ainvoke(meta_action_sequence)
    with open("meta_action_sequence.txt", "a", encoding="utf-8") as f:
        f.write(str(meta_action_sequence.meta_action_sequence))
    return {"meta_seq": meta_action_sequence.meta_action_sequence}
# async def replan_step(state: PlanExecute):
#     try:
#         output = await replanner.ainvoke(state)
#         if isinstance(output.action, Response):
#             return {"response": output.action.response}
#         elif isinstance(output.action, Plan):
#             return {"plan": output.action.steps}
#         else:
#             return {
#                 "response": "Unable to determine next action. Please provide more information."
#             }
#     except Exception as e:
#         error_message = f"An error occurred while planning: {str(e)}"
#         return {"response": error_message}


# def should_end(state: PlanExecute) -> Literal["Executor", "__end__"]:
#     if "response" in state and state["response"]:
#         return "__end__"
#     else:
#         return "Executor"


# # 创建工作流
workflow = StateGraph(PlanExecute)
workflow.add_node("Objectives_planner", generate_daily_objective)
workflow.add_node("detailed_planner", generate_detailed_plan)
workflow.add_node("meta_action_sequence", generate_meta_action_sequence)
# workflow.add_node("Executor", execute_step)
# workflow.add_node("replan", replan_step)
workflow.add_edge(START, "Objectives_planner")
workflow.add_edge("Objectives_planner", "detailed_planner")
workflow.add_edge("detailed_planner", "meta_action_sequence")
workflow.add_edge("meta_action_sequence", END)
# workflow.add_edge("Executor", "replan")
# workflow.add_conditional_edges("replan", should_end)

app = workflow.compile()


# 主函数
async def main():
    config = {"recursion_limit": 10}
    test_cases = [
        # {"input": "go to the farm, do a freelance job for 2 hours, then go home and sleep for 8 hours"},
        # {"input": "study for 3 hours, then do a public job for 4 hours"},
        {
            "input": """userid=8,
            username="Henry",
            gender="男",
            slogan="到处走走",
            description="闲不住，喜欢到处旅行",
            role="旅行家",
            task="每天至少去三个地方，即使重复了也要去",
            """
        },
        # {"input": "check character stats and inventory, then go to the hospital to see a doctor"},
        # {"input": "navigate to the park, start a conversation with user123 saying 'Hello!', then end the conversation"},
        # {"input": "do a freelance job for 4 hours, study for 2 hours, then sleep for 6 hours"},
        # {"input": "check character stats, do a public job for 3 hours, then study for 2 hours"},
        # {"input": "navigate to the gym, do a freelance job for 2 hours, then go home and sleep for 7 hours"},
    ]

    for case in test_cases:
        print(f"\nTest case: {case['input']}")
        try:
            async for event in app.astream(case, config=config):
                for k, v in event.items():
                    if k != "__end__":
                        print(v)
        except Exception as e:
            print(f"An error occurred: {e}")


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
