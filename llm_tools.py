from langchain_community.llms import Ollama
from openai import OpenAI
import openai
import requests
import json
from loguru import logger


class Caller:
    def __init__(self, model, base_url):
        self.model = model
        self.base_url = base_url

    def call_api(self, system_prompt, user_prompt, **kwargs):
        raise NotImplementedError("Subclass must implement abstract method")


class GPTCaller(Caller):
    def __init__(self, model="gpt-4o-mini", base_url="https://api.aiproxy.io/v1"):
        super().__init__(model=model, base_url=base_url)
        self.api_key = "sk-tejMSVz1e3ziu6nB0yP2wLiaCUp2jR4Jtf4uaAoXNro6YXmh"
        self.client = openai.Client(base_url=self.base_url, api_key=self.api_key)

    def call_api(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=self.model,
            **kwargs,
        )
        content = response.choices[0].message.content
        return content


class QwenCaller(Caller):
    def __init__(
        self,
        model="Qwen/Qwen2-72B-Instruct-GPTQ-Int8",
        base_url="http://143.89.16.145:5009/v1",
    ):
        super().__init__(model=model, base_url=base_url)
        self.api_key = "EMPTY"
        self.STREAM_SIG = False
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def call_api(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=self.STREAM_SIG,
        )
        content = response.choices[0].message.content
        return content


class Phi3Caller(Caller):
    def __init__(self, model="phi3", base_url="http://localhost:11434/"):
        super().__init__(model=model, base_url=base_url)

    def call_api(self, system_prompt, user_prompt):
        logger.info(
            f"Calling {self.model} with system prompt:\n{system_prompt}\nuser prompt:\n{user_prompt}\n"
        )
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        response = requests.post(self.base_url + "api/chat", json=data)
        content = json.loads(response.text)["message"]["content"]
        logger.info(f"{self.model} response:\n{content}")
        return content

    def get_llm(self):
        return Ollama(model=self.model, base_url=self.base_url)


class LlamaCaller(Caller):
    def __init__(self, model="llama3", base_url="http://localhost:11434/"):
        super().__init__(model=model, base_url=base_url)

    def call_api(self, system_prompt, user_prompt):
        logger.info(
            f"Calling {self.model} with system prompt:\n{system_prompt}\nuser prompt:\n{user_prompt}\n"
        )
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        response = requests.post(self.base_url + "api/chat", json=data)
        content = json.loads(response.text)["message"]["content"]
        logger.info(f"{self.model} response:\n{content}")
        return content

    def get_llm(self):
        return Ollama(model=self.model, base_url=self.base_url)
