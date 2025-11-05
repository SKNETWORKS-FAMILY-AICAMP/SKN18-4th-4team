import environ, os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]  # SKN18-4th-4Team/
env = environ.Env()
# 우선순위: .env → .env.local → (옵션) ENV_FILE로 지정된 경로
for f in [BASE_DIR/".env", BASE_DIR/".env.local"]:
    if f.exists():
        environ.Env.read_env(f)
# 필요하면 os.getenv("ENV_FILE")로 추가 로딩
