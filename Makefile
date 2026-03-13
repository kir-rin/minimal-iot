# IoT 환경 모니터링 프로젝트 Makefile
# UV + Docker 기반 개발 환경

.PHONY: help init install-backend install-backend-dev install-frontend dev-backend dev-frontend dev-all dev-docker db-up db-down migrate migrate-create test test-backend lint-backend build-backend build-frontend build-all clean logs-backend shell-backend logs-frontend shell-frontend open-browser

# 기본 목표
.DEFAULT_GOAL := help

# 색상 정의
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
NC := \033[0m # No Color

# OS 감지 (브라우저 열기용)
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
	OPEN_CMD := xdg-open
else ifeq ($(UNAME_S),Darwin)
	OPEN_CMD := open
else
	OPEN_CMD := start
endif

# ========== Quick Start ==========

init: ## 초기 설정 + 전체 실행 + 브라우저 자동 열기 (처음 실행 시)
	@echo "$(GREEN)🚀 초기화 시작...$(NC)"
	@$(MAKE) install-backend-dev
	@echo "$(GREEN)📦 Docker 전체 스택 실행...$(NC)"
	@docker-compose up -d
	@echo "$(YELLOW)서비스 준비 중... (10초 대기)$(NC)"
	@sleep 10
	@echo "$(GREEN)🗄️  데이터베이스 마이그레이션 실행...$(NC)"
	@docker-compose exec -T backend alembic upgrade head || echo "$(YELLOW)마이그레이션 이미 적용됨 또는 스킵$(NC)"
	@echo "$(GREEN)✅ 초기화 완료!$(NC)"
	@$(MAKE) open-browser
	@echo ""
	@echo "$(BLUE)📋 서비스 접속 정보:$(NC)"
	@echo "  - Frontend:     http://localhost"
	@echo "  - Backend API:  http://localhost:8000"
	@echo "  - API Docs:     http://localhost:8000/docs"



open-browser: ## 브라우저에서 서비스 URL 자동 열기
	@echo "$(GREEN)🌐 브라우저에서 서비스 열기...$(NC)"
	@$(OPEN_CMD) http://localhost:8000/docs 2>/dev/null || echo "$(YELLOW)API 문서: http://localhost:8000/docs$(NC)"
	@sleep 1
	@$(OPEN_CMD) http://localhost 2>/dev/null || echo "$(YELLOW)Frontend: http://localhost$(NC)"

help: ## 사용 가능한 명령어 목록 보기
	@echo "$(BLUE)IoT 환경 모니터링 프로젝트 - 사용 가능한 명령어:$(NC)"
	@echo ""
	@echo "$(GREEN)[🚀 Quick Start]$(NC)"
	@echo "  make init                 - 초기 설정 + 실행 + 브라우저 열기 ⭐ 처음 실행 시"
	@echo "  make dev-docker           - 전체 스택 Docker 실행 + 브라우저 자동 열기"
	@echo ""
	@echo "$(GREEN)[의존성 설치]$(NC)"
	@echo "  make install-backend      - 백엔드 의존성 설치"
	@echo "  make install-backend-dev  - 백엔드 개발 의존성 포함 설치"
	@echo "  make install-frontend     - 프론트엔드 의존성 설치"
	@echo ""
	@echo "$(GREEN)[개발 서버]$(NC)"
	@echo "  make dev-backend          - 백엔드 개발 서버 실행 (hot reload)"
	@echo "  make dev-frontend         - 프론트엔드 개발 서버 실행"
	@echo "  make dev-all              - 백엔드 + 프론트엔드 동시 실행"
	@echo "  make dev-docker           - 전체 스택 Docker로 실행"
	@echo ""
	@echo "$(GREEN)[데이터베이스]$(NC)"
	@echo "  make db-up                - PostgreSQL Docker 실행"
	@echo "  make db-down              - DB 중지 및 볼륨 삭제"
	@echo "  make migrate              - Alembic 마이그레이션 실행 (Docker 안에서)"
	@echo "  make migrate-create       - 새 마이그레이션 생성 (Docker 안에서, message=M 필요)"
	@echo ""
	@echo "$(GREEN)[테스트/빌드]$(NC)"
	@echo "  make test                 - 전체 테스트 실행"
	@echo "  make test-backend         - 백엔드 테스트만 실행"
	@echo "  make lint-backend         - 백엔드 린트 검사"
	@echo "  make build-backend        - 백엔드 Docker 이미지 빌드"
	@echo "  make build-frontend       - 프론트엔드 빌드"
	@echo "  make build-all            - 전체 Docker 빌드"
	@echo ""
	@echo "$(GREEN)[유틸리티]$(NC)"
	@echo "  make clean                - 캐시, 컨테이너, 빌드 파일 정리"
	@echo "  make logs-backend         - 백엔드 로그 확인"
	@echo "  make shell-backend        - 백엔드 컨테이너 쉘 접속"
	@echo "  make logs-frontend        - 프론트엔드 로그 확인"
	@echo "  make shell-frontend       - 프론트엔드 컨테이너 쉘 접속"

# ========== 의존성 설치 ==========

install-backend: ## 백엔드 의존성 설치
	@echo "$(BLUE)백엔드 의존성 설치 중...$(NC)"
	uv pip install -e .

install-backend-dev: ## 백엔드 개발 의존성 포함 설치
	@echo "$(BLUE)백엔드 개발 의존성 설치 중...$(NC)"
	uv pip install -e ".[dev]"

install-frontend: ## 프론트엔드 의존성 설치
	@echo "$(BLUE)프론트엔드 의존성 설치 중...$(NC)"
	cd frontend && npm install

# ========== 개발 서버 ==========

dev-backend: ## 백엔드 개발 서버 실행 (hot reload)
	@echo "$(GREEN)백엔드 개발 서버 시작...$(NC)"
	uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## 프론트엔드 개발 서버 실행
	@echo "$(GREEN)프론트엔드 개발 서버 시작...$(NC)"
	cd frontend && npm run dev

dev-all: ## 백엔드 + 프론트엔드 동시 실행
	@echo "$(GREEN)백엔드와 프론트엔드 동시 실행...$(NC)"
	@echo "$(YELLOW)주의: 두 서버가 병렬로 실행됩니다. 종료하려면 Ctrl+C를 누르세요.$(NC)"
	@trap 'kill %1; kill %2' SIGINT; \
		(make dev-backend &); \
		(make dev-frontend &); \
		wait

dev-docker: ## 전체 스택 Docker로 실행 + 브라우저 자동 열기
	@echo "$(GREEN)Docker Compose로 전체 스택 실행...$(NC)"
	@docker-compose up -d
	@echo "$(YELLOW)서비스 준비 중... (5초 대기)$(NC)"
	@sleep 5
	@$(MAKE) open-browser
	@echo ""
	@echo "$(BLUE)📋 서비스 접속:$(NC)"
	@echo "  - Frontend:     http://localhost"
	@echo "  - Backend API:  http://localhost:8000"
	@echo "  - API Docs:     http://localhost:8000/docs"

# ========== 데이터베이스 ==========

db-up: ## PostgreSQL Docker 실행
	@echo "$(GREEN)PostgreSQL 데이터베이스 시작...$(NC)"
	docker-compose up -d db
	@echo "$(YELLOW)DB가 준비될 때까지 기다리는 중...$(NC)"
	@sleep 3
	@docker-compose exec db pg_isready -U user -d iot_db || echo "$(YELLOW)DB가 아직 준비되지 않았습니다. 잠시 후 다시 확인하세요.$(NC)"

db-down: ## DB 중지 및 볼륨 삭제
	@echo "$(YELLOW)PostgreSQL 데이터베이스 중지 및 삭제...$(NC)"
	docker-compose down -v db

migrate: ## Alembic 마이그레이션 실행 (Docker 컨테이너 안에서)
	@echo "$(BLUE)Alembic 마이그레이션 실행 (Docker)...$(NC)"
	@docker-compose exec -T backend alembic upgrade head

migrate-create: ## 새 마이그레이션 생성 (Docker 컨테이너 안에서, message=M 필요)
ifndef message
	@echo "$(YELLOW)오류: message 변수가 필요합니다.$(NC)"
	@echo "사용법: make migrate-create message=\"마이그레이션 설명\""
	@exit 1
endif
	@echo "$(BLUE)새 마이그레이션 생성: $(message) (Docker)...$(NC)"
	@docker-compose exec -T backend alembic revision --autogenerate -m "$(message)"

# ========== 테스트/빌드 ==========

test: ## 전체 테스트 실행
	@echo "$(GREEN)전체 테스트 실행...$(NC)"
	uv run pytest

test-backend: ## 백엔드 테스트만 실행
	@echo "$(GREEN)백엔드 테스트 실행...$(NC)"
	uv run pytest tests/ -v

lint-backend: ## 백엔드 린트 검사
	@echo "$(BLUE)백엔드 린트 검사...$(NC)"
	@command -v ruff >/dev/null 2>&1 && uv run ruff check . || echo "$(YELLOW)ruff가 설치되지 않았습니다.$(NC)"

build-backend: ## 백엔드 Docker 이미지 빌드
	@echo "$(BLUE)백엔드 Docker 이미지 빌드...$(NC)"
	docker-compose build backend

build-frontend: ## 프론트엔드 빌드
	@echo "$(BLUE)프론트엔드 빌드...$(NC)"
	cd frontend && npm run build

build-all: ## 전체 Docker 빌드
	@echo "$(BLUE)전체 Docker 이미지 빌드...$(NC)"
	docker-compose build

# ========== 유틸리티 ==========

clean: ## 캐시, 컨테이너, 빌드 파일 정리
	@echo "$(YELLOW)정리 중...$(NC)"
	@echo "Docker 컨테이너 중지..."
	@docker-compose down 2>/dev/null || true
	@echo "Python 캐시 파일 삭제..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "UV 캐시 정리..."
	@uv cache clean 2>/dev/null || true
	@echo "$(GREEN)정리 완료!$(NC)"

logs-backend: ## 백엔드 로그 확인
	@docker-compose logs -f backend

shell-backend: ## 백엔드 컨테이너 쉘 접속
	@docker-compose exec backend sh

logs-frontend: ## 프론트엔드 로그 확인
	@docker-compose logs -f frontend

shell-frontend: ## 프론트엔드 컨테이너 쉘 접속
	@docker-compose exec frontend sh
