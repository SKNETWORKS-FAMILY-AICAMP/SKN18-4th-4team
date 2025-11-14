# nodes/classifier.py
from openai import OpenAI
from graph.state import SelfRAGState
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from graph.state import SelfRAGState


class HFModelClient:
    def __init__(self, model_name: str = "aaditya/Llama3‑OpenBioLLM‑8B"):
        # 허깅페이스 모델 로딩
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", torch_dtype=torch.bfloat16)
    
    def chat(self, prompt: str):
        # 입력 프롬프트를 토크나이즈
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        # 모델 실행하여 응답 생성
        outputs = self.model.generate(**inputs, max_new_tokens=200)
        
        # 출력 텍스트 디코딩
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

client = OpenAI() # env의 LLM_PROVIDER를 읽어서 판단
# clinet = HFModelClient() # 허깅페이스


def classifier(state: SelfRAGState) -> SelfRAGState:
    """
    Classifier 노드
    사용자 질문이 의학 관련 여부를 판별
    """

    query = state.get("question", "").strip()

    # 시작 로그
    print(f"• [Classifier] start (question=\"{query[:50]}...\")")

    if not query:
        state["need_quit"] = True
        print(f"• [Classifier] complete (need_quit=True)")
        return state

    prompt = f"""
    사용자의 질문:
    ---
    {query}
    ---
    이 질문이 의학, 건강, 질병, 증상, 치료 등과 관련된 질문입니까?

    '의학 관련' 또는 '의학 무관' 중 하나만 출력하세요.
    """

    res = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    # res = client.chat(prompt) # 허깅페이스

    result = res.choices[0].message.content.strip()
    # result = res.??? # 메시지 출력 확인

    if "의학 무관" in result:
        state["need_quit"] = True
    else:
        state["need_quit"] = False

    # 완료 로그
    print(f"• [Classifier] complete (need_quit={state['need_quit']})")

    return state
