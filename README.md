# IoT 환경 모니터링 백엔드

Python 기반 IoT 환경 모니터링 시스템 백엔드

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
1. ✅ 백엔드 의존성 설치
2. ✅ Docker 전체 스택 실행 (DB + Backend + Frontend)
3. ✅ 데이터베이스 마이그레이션
4. ✅ 🌱 **테스트 데이터 자동 생성**
5. ✅ 브라우저 자동 열기

**자동으로 열리는 URL:**
- 🌐 **Frontend:** http://localhost
- 📖 **API Docs:** http://localhost:8000/docs (자동으로 브라우저에 열림)

**수동 접속:**
- Backend API: http://localhost:8000

## Makefile 명령어

**🚀 Quick Start:**
- `make init` - 초기 설정 + 실행 + 브라우저 자동 열기 ⭐ 처음 실행 시
- `make dev-docker` - 전체 스택 Docker 실행 + 브라우저 자동 열기

**의존성 설치:**
- `make install-backend` - 백엔드 의존성 설치
- `make install-backend-dev` - 백엔드 개발 의존성 포함 설치
- `make install-frontend` - 프론트엔드 의존성 설치

**개발 서버:**
- `make dev-backend` - 백엔드 로컬 개발 서버 (hot reload)
- `make dev-frontend` - 프론트엔드 개발 서버
- `make dev-all` - 백엔드 + 프론트엔드 동시 실행

**데이터베이스:**
- `make db-up` - PostgreSQL Docker 실행
- `make db-down` - DB 중지 및 볼륨 삭제
- `make migrate` - Alembic 마이그레이션 실행 (Docker 안에서)
- `make migrate-create message="..."` - 새 마이그레이션 생성

**테스트/빌드:**
- `make test` - 전체 테스트 실행
- `make test-backend` - 백엔드 테스트만 실행
- `make lint-backend` - 백엔드 린트 검사
- `make build-backend` - 백엔드 Docker 이미지 빌드
- `make build-frontend` - 프론트엔드 빌드
- `make build-all` - 전체 Docker 빌드
- `make clean` - 캐시, 컨테이너, 빌드 파일 정리

**유틸리티:**
- `make logs-backend` - 백엔드 로그 확인
- `make shell-backend` - 백엔드 컨테이너 쉘 접속
- `make logs-frontend` - 프론트엔드 로그 확인
- `make shell-frontend` - 프론트엔드 컨테이너 쉘 접속

**전체 명령어 보기:**
```bash
make help
```

## 프로젝트 구조

```
.
├── src/                 # 소스 코드
├── tests/              # 테스트 코드
├── migrations/         # 데이터베이스 마이그레이션
├── scripts/            # 유틸리티 스크립트
├── frontend/           # 프론트엔드 (Vite + React + TypeScript)
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
