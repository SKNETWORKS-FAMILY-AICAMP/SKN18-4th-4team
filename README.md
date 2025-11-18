# SKN18-4th-Team

## [팀]

| 이름    | 역할   | 세부 역할 |   
|:------: |:-----: |:-------------------: |  
| 정동석  | 팀장   | RAG, LangGraph  |   
| 최준호  | 팀원   | 데이터 전처리 |   
| 이상효  | 팀원   | 데이터 전처리, RAG, Memory |   
| 안시현  | 팀원   | LangGraph |    
| 정인하  | 팀원   | LangGraph, Memory |   
| 황혜진  | 팀원   | WEB | 

## [주제]

### **🧬 MedAI Research**
> 의료 연구 AI 어시스턴트  
> LLM을 연동한 내·외부 문서 기반 질의응답 웹페이지

### 📌 서비스 개요
MedAI Research는 의료 연구·임상 진료·학술 활동에서 반복되는 **논문 검색·가이드라인 확인·임상 지침 비교**에 드는 시간을 줄이기 위해 설계된 **AI 기반 Evidence Assistant** 입니다.  
 의학 지식은 오류가 허용되지 않기 때문에, 단순 요약이나 일반적인 생성형 답변이 아닌  
 **“근거 기반(Evidence-Based)”**, **“출처가 명확한”**, **“재현 가능한”** 답변을 제공하는 것이 핵심입니다.

### **✔ 핵심 목표**
* **최신 논문·가이드라인 기반**의 신뢰 가능한 답변 제공  
* 반복적이고 시간이 많이 드는 문헌 검색·근거 비교 프로세스를 자동화  
* 의료 연구자·의사·대학원생들이 **임상적 판단 근거**를 빠르게 확보할 수 있도록 지원  
* RAG + LangGraph 기반으로 **추론 품질, 신뢰성, 근거 재현성**을 확보  
* 필수 의료 지식 **1.5만 Q&A + 전문 의료 문서 + 교과서** 기반 지식 그래프 활용

### 🎯 타겟 사용자
* 의료 연구자(Researcher)  
* 임상의(Physician)  
* 의과대학 대학원생(Medical Grad Student)  
* 임상시험 코디네이터(Clinical Trial Coordinator)

### 🎯 타겟 요구사항
* 최신 가이드라인·논문 근거를 빠르게 확인하고, 진료 의사결정을 위한 **정확한 근거 중심 답변**을 필요로 함.
* 논문 구조 요약, 연구방법 해석, 발표 준비를 위한 **체계적·단계별 요약 기능**과 후속 질문 생성이 필요함.
* Eligibility 조건, ECOG/lab cutoff 등 기준 정보를 **정확하게 정규화·추출**해주는 기능을 요구함.
* 특정 biomarker/outcome 기준으로 **연관 연구 탐색**, 근거 스니펫 추출, 비교 가능한 정리 기능이 필요함.

## [프로젝트 구조]

```text  
SKN18-4th-4team/  
├─ infra/                     # 로컬/배포 인프라 구성  
│  ├─ docker-compose.yml      # Postgres+pgvector+Django 컨테이너 오케스트레이션  
│  └─ nginx.conf              # 배포용 리버스 프록시 설정  
├─ scripts/                   # 데이터베이스/임베딩 파이프라인을 돌리는 독립 스크립트 모음  
│  ├─ init_db.sql             # pgvector 확장 및 기본 스키마 생성  
│  └─ init_models.sql/.py     # RAG 모델 구조 초기화/등록  
├─ django_app/                # Django 기반 웹/백오피스/챗봇 API  
│  ├─ manage.py               # Django 관리자 CLI 엔트리  
│  ├─ config/                 # settings/env 로더/urls/wsgi/asgi 등 전역 설정  
│  ├─ accounts/               # 인증·권한·프로필 관련 앱  
│  ├─ chat/                   # 챗봇 도메인의 모델, 서비스, API, LLM 연동  
│  ├─ main/                   # 랜딩 및 일반 페이지 뷰  
│  ├─ templates/              # SSR 템플릿(base, partials, 앱별 화면)  
│  ├─ static/                 # 원본 정적 리소스(css/js/img)  
│  └─ uploads/                # 사용자 업로드 파일(예: 프로필 이미지)  
├─ graph/                     # LangGraph 기반 LLM 워크플로 정의  
│  ├─ compile.py              # 그래프 빌드 엔트리포인트  
│  ├─ state.py                # 공유 state 스키마 및 업데이트 로직  
│  ├─ llm_client.py           # LLM 추상화/호출 래퍼  
│  ├─ nodes/                  # classifier/retrieval/answer/web-search 등 개별 노드  
│  ├─ memory/                 # 체크포인터·대화 기록 영속화  
│  └─ data/                   # 그래프 실행 예시/샘플 상태  
├─ rag/                       # RAG 데이터 계층 + ETL 파이프라인  
│  ├─ schema/                 # 문서/청크/임베딩 스키마 SQL  
│  ├─ queries/                # 검색·유지보수·통계 SQL 및 chat_memory.sqlite3  
│  ├─ services/               # embedder/retriever/vectorstore/DB 풀 모듈  
│  ├─ etl/                    # extract/transform/embed/load 단계 스크립트  
│  │  ├─ extract/             # 원천 데이터 적재 템플릿  
│  │  ├─ transform/           # 파싱·클리닝·청킹 도구  
│  │  ├─ embed/               # 임베딩 생성 러너  
│  │  └─ load/                # DB 적재 및 인덱스 빌더  
│  └─ data/                   # 문서/청크/임베딩 샘플 데이터  
└─ graph/ask.py               # LangGraph와 Django 중간 호출 유틸  
```

## [도구/기술]

#### **Environment**    
![Visual Studio Code](https://img.shields.io/badge/Visual%20Studio%20Code-007ACC?style=for-the-badge&logo=Visual%20Studio%20Code&logoColor=white)    
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=Git&logoColor=white)    
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white)    
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)  

#### **Development**    
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)    
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)    
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)  

#### **Database / Infrastructure**    
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)    
![pgvector](https://img.shields.io/badge/pgvector-4B8BBE?style=for-the-badge&logo=postgresql&logoColor=white)    
![SQLite3](https://img.shields.io/badge/SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)  

#### **Communication**    
![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)

## [요구사항]

**1️⃣ 데이터 수집 및 전처리 모듈**
- 의학 문헌(가이드라인, 논문, 교과서, 동의서 등)을 안정적으로 수집하고, RAG에 활용할 수 있는 정제된 텍스트 데이터로 변환한다.

**2️⃣ 질의 응답 플로우 설계 및 구축 (LangGraph 기반 오케스트레이션)**
- 의료 질문이 들어왔을 때, 일관된 흐름으로 처리되도록 LangGraph 기반 워크플로우를 설계한다.
- LangGraph는 다음 노드들을 그래프 형태로 연결하여,  질문 1건당 하나의 “추론 파이프라인”으로 실행되도록 구성.
- 메모리 → 질문 분류 → 용어 판별 → 검색/웹서치 → 검증 → 답변 생성 → 메모리 기록 → 답변 출력

**3️⃣ RAG ETL 파이프라인 (pgvector 기반)**
- 내외부 의료 문서를 RAG용 벡터 인덱스로 변환하는 ETL 파이프라인 구축

**4️⃣ 웹 UI & 시각화 (Django SSR + JS)**
- 연구자/의사가 실제로 사용할 수 있는 웹 인터페이스를 제공하고,  AI 대화·근거·통계를 한 화면에서 확인할 수 있게 한다.**

**5️⃣ 관측·품질·로그 (Observability & Quality Tracking)**
- 서비스 운영 중 무슨 질문에 어떤 답이 나갔고, 근거와 품질이 어땠는지 추적 가능하게 만든다.**

## [수집 데이터]
- AI-Hub 필수 의료 지식 : https://www.aihub.or.kr/aihubdata/data/view.do?&aihubDataSe=data&dataSetSn=71875

## [화면 구성]

- **도구** : Figma, HTML, CSS, Javascript

<img width="1659" height="1001" alt="Image" src="https://github.com/user-attachments/assets/91f3a335-a66b-42a2-99e7-4aabc8f3fea6" />

<img width="1645" height="1010" alt="Image" src="https://github.com/user-attachments/assets/8d374fa9-99d9-4feb-8d68-118dde04d28d" />

<img width="1662" height="1006" alt="Image" src="https://github.com/user-attachments/assets/2770e24d-6903-43c9-8ac1-d6b5a12fb0cd" />

<img width="1654" height="1007" alt="Image" src="https://github.com/user-attachments/assets/8e13d015-9954-40d0-85ae-a512059373dd" />

<img width="1665" height="1007" alt="Image" src="https://github.com/user-attachments/assets/1d154ec5-4634-4957-a9fe-dc5031373d40" />




<img width="1664" height="1007" alt="Image" src="https://github.com/user-attachments/assets/037d2858-0dfe-489b-9547-912f0a65608a" />

<img width="1661" height="1005" alt="Image" src="https://github.com/user-attachments/assets/ee71e97e-663b-40a6-92e9-a9d21ea36d0d" />
