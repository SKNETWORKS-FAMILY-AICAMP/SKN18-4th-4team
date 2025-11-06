** 여기에 RAG/LangGraph/Web 각각 실행 관련 내용 순서대로 적어주세요 **


---

# 공통

- Python Version 3.12.x
```bash
uv venv .venv --python 3.12
.venv/Scripts/activate
uv pip install -r requirements.txt
```
- Docker
```bash
# windows
docker-compose -f infra/docker-compose.yml up -d
# mac
docker compose -f infra/docker-compose.yml up -d
```

- PostgreSQL 접속
  - host: localhost
  - port: 5432
  - Database: sknproject4
  - username: .env.example 참고
  - pwd: .env.example 참고

---

# RAG
- ETL





---

# LangGraph







---

# Web

```
cd django-app
```
