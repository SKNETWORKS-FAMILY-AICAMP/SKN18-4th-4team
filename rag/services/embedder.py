'''
목적: 임베딩 모델을 사용하기 위한 공통 인터페이스
역할:
임베딩 모델을 로드하고 관리
텍스트를 벡터로 변환하는 기능 제공
다른 코드에서 임베딩 모델을 쉽게 호출할 수 있게 해주는 "도구"
'''
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
import psycopg2
from pgvector.psycopg2 import register_vector
load_dotenv()



def get_embedding_model_openai(
    model_name: str = "text-embedding-3-small"):
    """
    LangChain에서 사용할 OpenAIEmbeddings 인스턴스를 리턴합니다.
    .env에 OPENAI_API_KEY가 들어있어야 하며, 자동으로 불러옵니다.
    """
    load_dotenv()
    return OpenAIEmbeddings(
        model=model_name,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

# pgvector 연동
def get_pg_conn():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
    # 연결된 커넥션에 vector 타입 등록
    register_vector(conn)
    return conn


def get_embedding(text: str):
    """
    입력된 텍스트를 벡터로 변환하여 반환합니다.
    OpenAI 임베딩 모델과 .env 설정을 활용합니다.
    """
    # 환경변수에서 키와 모델 이름을 불러옴 (기본값 지정)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    # 환경변수에서 임베딩 모델명을 가져오고, 없으면 기본값("text-embedding-3-small")을 사용합니다.
    embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    # OpenAI 클라이언트 생성
    client = OpenAI(api_key=openai_api_key)
    # 임베딩 생성
    response = client.embeddings.create(
        model=embed_model,
        input=text,
    )
    vector = response.data[0].embedding
    return vector
