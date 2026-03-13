# IoT 환경 모니터링 백엔드

Python 기반 IoT 환경 모니터링 시스템 백엔드

## 목차

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [프로젝트 구조](#프로젝트-구조)
- [UV 설치](#uv-설치-로컬-개발-시)
- [주요 기술 스택](#주요-기술-스택)
- [추가로 구현한 것](#추가로-구현한-것)
- [API Specification](docs/API_SPECIFICATION.md)
- [Database Schema](docs/DB_SCHEMA.md)

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (로컬 개발 시에만 필요)
- UV (선택사항, 로컬 개발 시)

## Quick Start

```bash
# 처음 실행할 때 (한 번에 모든 설정 + 실행 + 테스트 데이터 + 브라우저 자동 열기)
make init

# 이후에는 (실행 + 브라우저 자동 열기)
make dev-docker
```

**`make init`이 자동으로 수행하는 것:**
1. 백엔드 의존성 설치
2. Docker 전체 스택 실행 (DB + Backend + Frontend)
3. 데이터베이스 마이그레이션
4. 테스트 데이터 자동 생성
5. 브라우저 자동 열기

**자동으로 열리는 URL:**
- **Frontend:** http://localhost
- **API Docs:** http://localhost:8000/docs (자동으로 브라우저에 열림)

**수동 접속:**
- Backend API: http://localhost:8000

## 프로젝트 구조

```
.
├── src/                 # 소스 코드
├── tests/              # 테스트 코드
├── migrations/         # 데이터베이스 마이그레이션
├── scripts/            # 유틸리티 스크립트
├── frontend/           # 프론트엔드 (Vite + React + TypeScript)
├── docs/               # 문서 (API 명세, DB 스키마 등)
├── pyproject.toml      # 프로젝트 설정 (UV 사용)
├── docker-compose.yml  # Docker Compose 설정
├── Dockerfile.backend  # 백엔드 Docker 이미지
├── Dockerfile.frontend # 프론트엔드 Docker 이미지
└── Makefile           # 개발 편의성 명령어
```

## UV 설치 (로컬 개발 시)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 주요 기술 스택

**백엔드:**
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Alembic (마이그레이션)
- APScheduler

**프론트엔드:**
- Vite
- React 19
- TypeScript
- Tailwind CSS
- Recharts (차트)

**인프라:**
- Docker & Docker Compose
- UV (패키지 매니저)

## 추가로 구현한 것

### MQTT 호환성을 위한 Adapter 패턴

현재 HTTP 기반 API를 MQTT와도 호환될 수 있도록 Adapter 패턴을 적용했습니다.

- **Transport Layer**: `src/transports/`에 프로토콜 독립적인 인터페이스와 구현체
- **HTTP Transport**: 기존 Router에서 Service Layer 호출
- **향후 확장**: MQTT 브로커 도입 시 `MqttTransport`만 추가 구현하면 됨
- **상세 문서**: [docs/MQTT_ADAPTER_PLAN.md](docs/MQTT_ADAPTER_PLAN.md) 참조

---

## API Specification

API 엔드포인트 명세는 [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md)를 참조하세요.

## Database Schema

데이터베이스 스키마 정보는 [docs/DB_SCHEMA.md](docs/DB_SCHEMA.md)를 참조하세요.
