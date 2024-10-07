import os
import sys
import datetime
from itertools import cycle
from langchain import hub
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import *
from node_model import (
    PlanExecute,
    DailyObjective,
    DetailedPlan,
    MetaActionSequence,
    Reflection,
)
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
import asyncio
from tool_executor import execute_action_sequence

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongo_utils import insert_document
from database import config

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-tejMSVz1e3ziu6nB0yP2wLiaCUp2jR4Jtf4uaAoXNro6YXmh"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Bio3_agent"

API_KEYS = [
    "sk-tejMSVz1e3ziu6nB0yP2wLiaCUp2jR4Jtf4uaAoXNro6YXmh",
    "sk-hZAdcvHxCvE7psdje4SezVNHDqOLWO1Ar58sldOK7R741zK6",
    "sk-VTpN30Day8RP7IDVVRVWx4vquVhGViKftikJw82WIr94DaiC",
]

api_key_cycle = cycle(API_KEYS)


def get_llm(base_url="https://api.aiproxy.io/v1", model="gpt-4o-mini", temperature=0):
    api_key = next(api_key_cycle)
    print("Using API key:", api_key)
    return ChatOpenAI(
        base_url=base_url, model=model, api_key=api_key, temperature=temperature
    )


# 定义工具列表
tool_list = [
    navigate_to,
    do_freelance_job,
    sleep,
    work_change,
    get_character_stats,
    get_character_status,
    get_character_basic_info,
    get_inventory,
    submit_resume,
    vote,
    do_public_job,
    study,
    talk,
    end_talk,
    calculate_distance,
    trade,
    use_item,
    see_doctor,
    get_freelance_jobs,
    get_public_jobs,
    get_candidates,
    get_activity_subjects,
    get_talk_data,
    get_position,
    eat,
]

# llm-readable
tool_functions = """
1. do_freelance_job(): Perform freelance work
2. navigate_to(location): Navigate to a specified location
3. sleep(hours): Sleep for specified number of hours
4. work_change(): Change job
5. get_character_stats(): Get character statistics
6. get_character_status(): Get character status
7. get_character_basic_info(): Get character basic information
8. get_inventory(): Get inventory information
9. submit_resume(): Submit resume
10. vote(): Cast a vote
11. do_public_job(): Perform public work
12. study(hours): Study for specified number of hours
13. talk(person): Talk to a specified person
14. end_talk(): End conversation
15. calculate_distance(location1, location2): Calculate distance between two locations
16. trade(): Trade an item
17. use_item(item): Use an item
18. see_doctor(): Visit a doctor
19. get_freelance_jobs(): Get list of available freelance jobs
20. get_public_jobs(): Get list of available public jobs
21. get_candidates(): Get list of candidates
22. get_activity_subjects(): Get list of activity subjects
23. get_talk_data(): Get conversation data
24. get_position(): Get current position
25. eat(): Eat food
"""

locations = """
1. Home
2. Park
3. Restaurant
4. Hospital
5. School
6. Farm
"""


# 定义提示模板
obj_planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are the daily objectives planner in a RPG game. For the given user profile:\n
            Name: 
            Description: 
            Role: 
            Task: 
            Location: 
            Status: 
            Inventory: 
            \n
            and the past daily objectives are:
            {past_objectives}.
            \n
            Come up with a general daily objectives. Each daily objectives should be diverse and not repetitive. \n
            These objectives are daily objectives that ONLY related to the following tool functions.\n
            {tool_functions}\n


            The final format should be a list of daily objectives. Like this:\n
            ["Working: Working in the farm","Studying: Discover something about science", "Socializing: Try to make friends"]\n
            """,
        ),
        ("placeholder", "{messages}"),
    ]
)

# replanner_prompt = ChatPromptTemplate.from_template(
#     """For the given objective, come up with a simple step by step plan. \
# This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
# The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

# Additionally, if during the execution of a step you encounter a tool call with missing required parameters, randomly generate a reasonable parameter value to fill in, rather than throwing an error. For example, if a duration is needed but not specified, you might randomly choose a value between 1 and 8 hours.

# Your objective was this:
# {input}

# Your original plan was this:
# {plan}

# You have currently done the follow steps:
# {past_steps}

# Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
# )

detail_planner_prompt = ChatPromptTemplate.from_template(
    """For the given daily objectives,
    \n
    {daily_objective}
    \n
    come up with a detailed plan only associated with the available actions.\n
    actions_available:
    {tool_functions}
]\n
    The detailed plan may involve plans that are not in the daily objectives.(daily actions like eating meals, random actions like chatting with friends.)\n
    
    The final format should be a list of daily objectives. for example:\n
    Working: "I should navigate to the farm, then do a freelance job."\n,
    daily_action:"I should eat breakfast, lunch and dinner."\n,
    Study:"I should study"\n,
    Socializing:"Perhaps I should go to the square and talk to someone."\n
    
    """
)

meta_action_sequence_prompt = ChatPromptTemplate.from_template(
    """For the given detailed plan, think step by step to come up with a player action sequence only associated with the available actions/locations.\n
    {plan}
    \n
    
    actions_available:
    {tool_functions}
    \n
    Use navigate_to to go to the location. \n
    Every day, you start at home. \n
    You need to sleep everyday.\n
    locations_available:\n
    {locations}
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

reflection_prompt = ChatPromptTemplate.from_template(
    """Based on the following meta action sequence and their execution results, 
    provide a brief reflection on the success of the plan, any unexpected outcomes, 
    and potential improvements for future planning:

    Meta Action Sequence:
    {meta_seq}

    Execution Results:
    {execution_results}

    Reflection:
    """
)


# 创建规划器和重新规划器

obj_planner = obj_planner_prompt | get_llm(temperature=1).with_structured_output(
    DailyObjective
)
detail_planner = detail_planner_prompt | get_llm().with_structured_output(DetailedPlan)
meta_action_sequence_planner = (
    meta_action_sequence_prompt | get_llm().with_structured_output(MetaActionSequence)
)
meta_seq_adjuster = meta_seq_adjuster_prompt | get_llm().with_structured_output(
    MetaActionSequence
)
reflector = reflection_prompt | get_llm().with_structured_output(Reflection)


async def generate_daily_objective(state: PlanExecute):
    daily_objective = await obj_planner.ainvoke(
        {
            "messages": [("user", state["input"])],
            "tool_functions": state["tool_functions"],
            "locations": state["locations"],
            "past_objectives": state.get("past_objectives", []),
        }
    )
    # Prepare the document to insert
    document = {
        "userid": state["userid"],
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "objectives": daily_objective.objectives,
    }
    # Insert document using insert_document
    inserted_id = insert_document(config.daily_objective_collection_name, document)
    print(
        f"Inserted daily objective with id {inserted_id} for userid {document['userid']}"
    )

    return {"daily_objective": daily_objective.objectives}


async def generate_detailed_plan(state: PlanExecute):
    detailed_plan = await detail_planner.ainvoke(state)
    # Prepare the document to insert
    document = {
        "userid": state["userid"],
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "detailed_plan": detailed_plan.detailed_plan,
    }
    # Insert document using insert_document
    inserted_id = insert_document(config.plan_collection_name, document)
    print(
        f"Inserted detailed plan with id {inserted_id} for userid {document['userid']}"
    )

    return {"plan": detailed_plan.detailed_plan}


async def generate_meta_action_sequence(state: PlanExecute):
    meta_action_sequence = await meta_action_sequence_planner.ainvoke(state)
    meta_action_sequence = await meta_seq_adjuster.ainvoke(meta_action_sequence)
    # Prepare the document to insert
    document = {
        "userid": state["userid"],
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "meta_sequence": meta_action_sequence.meta_action_sequence,
    }
    # Insert document using insert_document
    inserted_id = insert_document(config.meta_seq_collection_name, document)
    print(
        f"Inserted meta action sequence with id {inserted_id} for userid {document['userid']}"
    )

    return {"meta_seq": meta_action_sequence.meta_action_sequence}


async def generate_reflection(state: PlanExecute):
    meta_seq = state.get("meta_seq", [])
    execution_results = state.get("execution_results", [])

    reflection = await reflector.ainvoke(
        {"meta_seq": meta_seq, "execution_results": execution_results}
    )

    # 准备要插入的文档
    document = {
        "userid": state["userid"],
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "meta_sequence": meta_seq,
        "execution_results": execution_results,
        "reflection": reflection.reflection,
    }

    # 使用 insert_document 插入文档
    inserted_id = insert_document(config.reflection_collection_name, document)
    print(f"Inserted reflection with id {inserted_id} for userid {document['userid']}")

    return {"reflection": reflection.reflection}


async def invoke_tool_executor(state: PlanExecute):
    meta_seq = state.get("meta_seq", [])
    print("Executing the following actions:")
    results = execute_action_sequence(meta_seq)
    execution_results = []
    for action, result in zip(meta_seq, results):
        print(f"Action: {action}")
        print(f"Result: {result}")
        execution_results.append({"action": action, "result": result})
    return {"execution_results": execution_results}


# # 创建工作流
workflow = StateGraph(PlanExecute)
workflow.add_node("Objectives_planner", generate_daily_objective)
workflow.add_node("detailed_planner", generate_detailed_plan)
workflow.add_node("meta_action_sequence", generate_meta_action_sequence)
workflow.add_node("tool_executor", invoke_tool_executor)
workflow.add_node("reflector", generate_reflection)

workflow.add_edge(START, "Objectives_planner")
workflow.add_edge("Objectives_planner", "detailed_planner")
workflow.add_edge("detailed_planner", "meta_action_sequence")
workflow.add_edge("meta_action_sequence", "tool_executor")
workflow.add_edge("tool_executor", "reflector")
workflow.add_edge("reflector", END)
app = workflow.compile()


# 主函数
async def main():
    config = {"recursion_limit": 10}
    test_cases = [
        {
            "userid": 1,
            "input": """userid=1,
            username="Alice",
            gender="女",
            slogan="知识就是力量",
            description="一个爱学习的大学生",
            role="学生",
            task="每天至少学习8小时，期末考试取得优异成绩",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 2,
            "input": """userid=2,
            username="Bob",
            gender="男",
            slogan="交易的艺术",
            description="一个精明的商人",
            role="商人",
            task="每天至少交易一次，寻找最佳交易机会",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 3,
            "input": """userid=3,
            username="Charlie",
            gender="女",
            slogan="探索未知",
            description="一个喜欢探险的冒险家",
            role="冒险家",
            task="每天至少探险一次，寻找宝藏",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 4,
            "input": """userid=4,
            username="David",
            gender="男",
            slogan="拯救世界",
            description="一个勇敢的科学家",
            role="科学家",
            task="每天至少发明一项新技术，解决一个世界问题",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 5,
            "input": """userid=5,
            username="Eve",
            gender="女",
            slogan="艺术的魅力",
            description="一个有才华的艺术家",
            role="艺术家",
            task="每天至少创作一幅画，展示艺术才华",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 6,
            "input": """userid=6,
            username="Frank",
            gender="男",
            slogan="Serve the people",
            description="Enthusiastic about community work, enjoys communicating with people and exploring different places",
            role="Ordinary Resident",
            task="Help complete community voting and election work, communicate with residents to understand their needs and ideas",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 7,
            "input": """userid=7,
            username="Grace",
            gender="女",
            slogan="Strive for a better life",
            description="Busy looking for a job, very occupied",
            role="Job Seeker",
            task="Submit resumes, attend interviews, and search for jobs every day",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 8,
            "input": """userid=8,
            username="Henry",
            gender="男",
            slogan="到处走走",
            description="闲不住，喜欢到处旅行",
            role="旅行家",
            task="每天至少去三个地方，即使重复了也要去",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 9,
            "input": """userid=9,
            username="Ivy",
            gender="女",
            slogan="Shopping makes me happy",
            description="A fashion blogger who enjoys purchasing various goods.",
            role="Shopping Enthusiast",
            task="Buy different things every day, acquire various items",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
        {
            "userid": 10,
            "input": """userid=10,
            username="Jack",
            gender="男",
            slogan="The world is big, I want to see it all",
            description="A traveler who loves to explore new places",
            role="Traveler",
            task="Visit at least three places every day, even if they are repeated",
            """,
            "tool_functions": tool_functions,
            "locations": locations,
        },
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
