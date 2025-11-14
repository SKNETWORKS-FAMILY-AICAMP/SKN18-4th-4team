# nodes/medical_check.py
from openai import OpenAI
from graph.state import SelfRAGState
from graph.state import SelfRAGState
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class HFModelClient:
    def __init__(self, model_name: str = "aaditya/Llama3-OpenBioLLM-8B"):
        print("• [HFModel] Loading model... (This may take some time)")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16
        )
        print("• [HFModel] Model loaded successfully.")

    def chat(self, prompt: str, max_new_tokens: int = 300) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.3,
        )

        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return result.strip()

client = OpenAI() # env의 LLM_PROVIDER를 읽어서 판단
# client = HFModelClient()


def medical_check(state: SelfRAGState) -> SelfRAGState:
    """
    의학 용어 질문 판단 노드
    질문이 의학 용어의 정의를 묻는지 판별
    """

    query = state.get("question", "").strip()

    # 시작 로그
    print(f"• [MedicalCheck] start (question=\"{query[:50]}...\")")

    prompt = f"""
    사용자의 질문:
    ---
    {query}
    ---
    이 질문이 의학 용어나 질병명의 '정의', '뜻', '의미'를 묻는 질문입니까?

    예시:
    - "당뇨병이 뭐야?" → 용어 질문
    - "고혈압의 정의는?" → 용어 질문
    - "당뇨병 치료 방법은?" → 용어 질문 아님
    - "두통이 있을 때 어떻게 해야 해?" → 용어 질문 아님

    '용어 질문' 또는 '일반 질문' 중 하나만 출력하세요.
    """

    res = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    # res = client.chat(prompt)

    result = res.choices[0].message.content.strip()
    # result = res.??? # 메시지 출력 확인

    if "용어" in result:
        state["is_terminology"] = True
    else:
        state["is_terminology"] = False

    # 완료 로그
    print(f"• [MedicalCheck] complete (is_terminology={state['is_terminology']})")

    return state
