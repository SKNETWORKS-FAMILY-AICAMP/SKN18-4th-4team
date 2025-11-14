# nodes/evaluate_chunk.py
from openai import OpenAI
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

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
# client = HFModelClient()

def evaluate_chunk(state):
    """
    청크 조사 노드
    검색된 문서 청크들의 관련성을 평가
    """
    query = state.get("question", "").strip()
    context = state.get("context", "")

    # 시작 로그
    context_len = len(context)
    print(f"• [EvaluateChunk] start (query=\"{query[:50]}...\", context_chars={context_len})")

    if not query or not context:
        state["relevance_score"] = 0.0
        state["is_relevant"] = False
        print(f"• [EvaluateChunk] complete (is_relevant=False, score=0.0)")
        return state

    prompt = f"""
    질문: {query}

    검색된 컨텍스트:
    ---
    {context}
    ---

    위 컨텍스트가 질문에 답변하기에 충분히 관련성이 있는지 평가하세요.

    다음 형식으로만 답변하세요:
    관련성: [높음/낮음]
    점수: [0.0-1.0 사이의 숫자]
    이유: [간단한 설명]`
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    # res = client.chat(prompt)

    result = res.choices[0].message.content.strip()
    # result = res.??? # 메시지 출력 확인

    # 관련성 평가 결과 파싱
    if "높음" in result:
        state["is_relevant"] = True
        state["relevance_score"] = 0.80  # 기본값
    else:
        state["is_relevant"] = False
        state["relevance_score"] = 0.30  # 기본값
    # 점수 추출 시도
    if "점수:" in result:
        try:
            score_part = result.split("점수:")[1].split("\n")[0].strip()
            state["relevance_score"] = round(float(score_part), 2)  # 소수점 2자리
        except:
            pass

    state["evaluation_result"] = result

    # 완료 로그
    print(f"• [EvaluateChunk] complete (is_relevant={state['is_relevant']}, score={state['relevance_score']})")

    return state
