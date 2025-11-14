# nodes/rewrite_query.py
from openai import OpenAI
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class HFModelClient:
    def __init__(self, model_name: str = "aaditya/Llama3-OpenBioLLM-8B"):
        print("• [HFModel] Loading model for QueryRewrite...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16
        )
        print("• [HFModel] Model loaded (rewrite_query).")

    def chat(self, prompt: str, max_new_tokens: int = 200) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.3,
        )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

client = OpenAI() # env의 LLM_PROVIDER를 읽어서 판단
# client = HFModelClient()

def rewrite_query(state):
    """
    질문 재작성 노드
    원래 질문을 더 명확하고 검색하기 쉽게 재작성
    """
    original_query = state.get("question", "").strip()

    # 시작 로그
    print(f"• [QueryRewrite] start (question=\"{original_query[:50]}...\")")

    if not original_query:
        state["rewritten_question"] = ""
        print(f"• [QueryRewrite] complete (rewritten=\"\")")
        return state

    # 평가 결과가 있다면 참고
    evaluation_result = state.get("evaluation_result", "")

    prompt = f"""
    원래 질문: {original_query}

    {f"이전 검색 평가 결과: {evaluation_result}" if evaluation_result else ""}

    위 질문을 더 명확하고 정보 검색에 적합하도록 재작성해주세요.
    재작성 시 다음을 고려하세요:
    1. 핵심 키워드를 명확히
    2. 모호한 표현을 구체화
    3. 검색 엔진이 이해하기 쉬운 형태로

    재작성된 질문만 출력하세요.
    """

    res = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    # res = client.chat(prompt, max_new_tokens=150)

    rewritten = res.choices[0].message.content.strip()
    # rewritten = res.??? # 허깅페이스 메세지 출력 확인

    # 재작성된 질문을 question 필드에 업데이트
    state["rewritten_question"] = rewritten
    state["question"] = rewritten  # 다음 검색에 사용될 수 있도록

    # 재작성 횟수 증가
    state["rewrite_count"] = state.get("rewrite_count", 0) + 1

    # 완료 로그
    print(f"• [QueryRewrite] complete (rewritten=\"{rewritten[:50]}...\", count={state['rewrite_count']})")

    return state
