-- 테이블/인덱스 초기 스키마

CREATE EXTENSION IF NOT EXISTS vector;

CREATE DATABASE skn_project;
\c skn_project;

-- (선택) 기본 계정/권한
CREATE USER skn WITH PASSWORD 'sknpass';
GRANT ALL PRIVILEGES ON DATABASE skn_project TO skn;

