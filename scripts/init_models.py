"""
선택된 Django 모델 테이블만 삭제해 CustomUser 마이그레이션을 처음부터 적용할 수 있게 한다.
사용법:
    ./.venv/bin/python scripts/init_models.py
환경 변수는 Django 설정과 동일하게 .env / .env.local 에서 읽는다.
"""

from __future__ import annotations

import os
from pathlib import Path

import environ
import psycopg2
from psycopg2 import sql


BASE_DIR = Path(__file__).resolve().parent.parent


def load_env() -> environ.Env:
    env = environ.Env()
    for f in [BASE_DIR / ".env", BASE_DIR / ".env.local"]:
        if f.exists():
            environ.Env.read_env(f)

    env_file = os.getenv("ENV_FILE")
    if env_file and Path(env_file).exists():
        environ.Env.read_env(env_file)
    return env


def drop_tables() -> None:
    env = load_env()
    conn = psycopg2.connect(
        dbname=env("POSTGRES_DB", default="sknproject4"),
        user=env("POSTGRES_USER", default="root"),
        password=env("POSTGRES_PASSWORD", default="root1234"),
        host=env("POSTGRES_HOST", default="localhost"),
        port=env("POSTGRES_PORT", default="5432"),
    )
    tables_to_drop = [
        # accounts / auth / admin / contenttypes / sessions
        "customUser",
        "accounts_customuser",
        "auth_user_user_permissions",
        "auth_user_groups",
        "auth_user",
        "auth_group_permissions",
        "auth_group",
        "auth_permission",
        "django_admin_log",
        "django_content_type",
        "django_session",
        "django_migrations",
        # app tables
        "chat_messagefeedback",
        "chat_message",
        "chat_chatconversation",
        "main_dashboardmetric",
    ]

    conn.autocommit = True
    dropped = []
    with conn, conn.cursor() as cur:
        for table in tables_to_drop:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(table)))
            dropped.append(table)
    conn.close()
    print("Dropped tables (if existed):")
    for name in dropped:
        print(f" - {name}")


if __name__ == "__main__":
    drop_tables()
