# etl 실행코드

    1. docker 연결

        cd ./infra/

        docker-compose up -d

    2. infra out

        cd ..

    3. .env 작성
    
        작성양식:

        ```
        
        # Django
        DJANGO_ENV=dev
        DJANGO_SECRET_KEY=dev-secret-key-123
        DJANGO_DEBUG=1
        ALLOWED_HOSTS=*

        # DB
        POSTGRES_HOST=127.0.0.1
        POSTGRES_PORT=5432
        POSTGRES_DB=sknproject4
        POSTGRES_USER=root
        POSTGRES_PASSWORD=root1234

        # LLM provider 선택: openai|ollama|huggingface
        LLM_PROVIDER=openai

        # OpenAI
        OPENAI_API_KEY="" <<<<<<<<<<<<<<<<<<<꼭 넣을 것!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        OPENAI_BASE_URL="https://api.openai.com/v1"

        # Huggingface
        HF_API_TOKEN=

        # 검색/RAG
        EMBED_MODEL_NAME=text-embedding-3-small
        PGVECTOR_DISTANCE=cosine
        TOP_K=5

        # 웹 포트 (로컬 호스트 바인딩)
        WEB_PORT=8000

        ```

    4. etl 실행 (전처리~임베딩까지)

        실행코드:

            python -m rag.etl.embed.embed_runner

---

# Data Cleaning

-데이터 클리닝 과정

    1. column_renewal.py:
        - 컬럼 재정의를 위한 파일
            - __source,domain,source, c_id, source_spec, creation_year 드랍
            - c_id, source_spec, creation_year 재조합
                - 재조합은 (source_spec)_(creation_year)_(c_id) 로
                    ex) guide_kr_2023_1182_1
                - 특이사항: 년도에 결측치 있음 --> 결측치 있으면 생략하고 컬럼데이터 냄
                    ex) guide_kr_1182_1
            - content는 유지
        
        - 로우데이터: merged_KOR.csv
        - 결과데이터: T1_column_renewed.csv

    2. num_spot_cleaning.py:
        - 숫자+온점(.) 클리닝을 위한 파일
            - 특이사항: 숫자+온점(.) 뒤에 공백도 strip() 진행

        - 로우데이터: T1_column_renewed.csv
        - 결과데이터: T2_numspot_renewed.csv

    3. drop_reference.py:
        - 인용구 드랍을 위한 파일
        - 번역 / 인용 구분 후 인용구만 드랍

        - 로우데이터: T2_numspot_renewed.csv
        - 결과데이터: T2_reference_dropped.csv

    4. cleaned_double_quotation.py:
        - 큰따옴표 클리닝을 위한 파일    
        - content 내에 있는 큰따옴표 클리닝

        - 로우데이터: T2_reference_dropped.csv
        - 결과데이터: T2_cleaned_quot.csv

    5. clean_cid_year
        - cid컬럼에서 연도가 2023.0으로 소수점까지 있음
        - 소수점만 드랍

        - 로우데이터: T2_cleaned_quot.csv
        - 결과데이터: T2_cleaned_cid_year.csv

    6. parentheses_strip.py
        - ( 5%) 같이 ( 뒤에 공백이 있는 부분 strip

        - 로우데이터: T2_cleaned_cid_year.csv
        - 결과데이터: T2_parenthesis_stripped.csv

---

# Chunking

1. chunked_spotnum.py:
    - . ! ? 갯수를 문장으로 인식, 카운트하고 2개 단위로 청킹

    - 로우데이터: T2_parenthesis_stripped.csv
    - 결과데이터: Data_Final.csv

---

# csv_loader



---

# embedding

1. OPENAI Model : text-embedding-3-small

2. batch_size=100

3. 비동기로 안함

4. Dimension_size = 1536

5. 소요시간 : 약 30분
