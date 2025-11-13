** 여기에 RAG/LangGraph/Web 각각 실행 관련 내용 순서대로 적어주세요 **


---

# 공통

1. Python Version 3.12.x
```bash
uv venv .venv --python 3.12
.venv/Scripts/activate
uv pip install -r requirements.txt
```
2. .env.example 파일 복사해서 .env 파일 생성
3. Docker
```bash
# windows
docker-compose -f infra/docker-compose.yml up -d
# mac
docker compose -f infra/docker-compose.yml up -d
```
4. PostgreSQL 접속
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
1. postgreSQL 실행 확인
3. 실행
```bash
python django_app/manage.py migrate
python django_app/manage.py runserver
```
1. 화면 접속 (메인 - 대시보드)
   - http://localhost:8000/main
2. Admin
   -  http://localhost:8000/admin/
   -  admin / admin1234

