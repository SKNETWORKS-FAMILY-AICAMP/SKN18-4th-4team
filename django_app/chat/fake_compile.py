"""
임시 응답 생성용 LangChain OpenAI 빌더.
실제 LangGraph compile이 준비되기 전까지 build()를 호출해
간단한 GPT 기반 응답을 받아온다.
"""

import random
from typing import Dict, List, TYPE_CHECKING

from .llm import get_llm
from langchain_core.messages import AIMessage

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

_REFERENCE_POOL = [
    {
        "title": "JSCCR Colon Cancer Guidelines",
        "journal": "Japanese Society for Cancer of the Colon and Rectum",
        "year": 2023,
        "doi": "10.1000/jsccr.guide",
    },
    {
        "title": "Submucosal Invasion Depth and Metastasis",
        "journal": "Clinical Gastroenterology",
        "year": 2022,
        "doi": "10.4321/cg.2022.015",
    },
    {
        "title": "MMP-9 Expression as Prognostic Marker",
        "journal": "Oncology Research",
        "year": 2024,
        "doi": "10.1016/onres.2024.002",
    },
    {
        "title": "TIMP-2 and Lymphatic Invasion",
        "journal": "Journal of Surgical Oncology",
        "year": 2021,
        "doi": "10.1186/jso.2021.777",
    },
]


def _generate_fake_citations() -> List[Dict]:
    count = random.randint(1, 3)
    picks = random.sample(_REFERENCE_POOL, k=count)
    citations = []
    for idx, item in enumerate(picks, start=1):
        citations.append(
            {
                "id": idx,
                "title": item["title"],
                "journal": item["journal"],
                "year": item["year"],
                "doi": item["doi"],
            }
        )
    return citations


class FakeCompileLLM:
    def __init__(self, llm: "ChatOpenAI"):
        self.llm = llm

    def invoke(self, messages):
        response = self.llm.invoke(messages)
        if not isinstance(response, AIMessage):
            response = AIMessage(content=str(response))
        extras = response.additional_kwargs or {}
        extras["citations"] = _generate_fake_citations()
        response.additional_kwargs = extras
        return response


def build():
    return FakeCompileLLM(get_llm())
