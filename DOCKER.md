# Docker 실행 가이드

## 환경 구성

- **PostgreSQL 18** - 데이터베이스
- **FastAPI Backend** - Python 3.11
- **React Frontend** - Node.js 20 + Nginx

## 실행 방법

### 1. Docker Compose로 전체 실행

```bash
docker-compose up --build
```

### 2. 백그라운드에서 실행

```bash
docker-compose up --build -d
```

### 3. 로그 확인

```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### 4. 서비스 중지

```bash
docker-compose down
```

### 5. 볼륨까지 삭제 (데이터 초기화)

```bash
docker-compose down -v
```

## 접속 정보

| 서비스 | URL | 설명 |
|--------|-----|------|
| Frontend | http://localhost | 메인 애플리케이션 |
| Backend API | http://localhost/api | REST API |
| Backend Health | http://localhost/api/health | 헬스체크 |
| PostgreSQL | localhost:5432 | 직접 접속 (선택) |

## 환경 변수

### Backend

- `DATABASE_URL`: PostgreSQL 연결 URL
- `SCHEDULER_ENABLED`: 스케줄러 활성화 (true/false)
- `APP_ENV`: 애플리케이션 환경 (development/production)

### Database

- `POSTGRES_USER`: user
- `POSTGRES_PASSWORD`: password
- `POSTGRES_DB`: iot_db

## 개발 환경에서의 실행

### Backend만 실행 (개발용)

```bash
# PostgreSQL만 실행
docker-compose up -d db

# 백엔드는 로컬에서 실행
source .venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend만 실행 (개발용)

```bash
cd frontend
npm run dev
```

## 문제 해결

### CORS 오류

Nginx가 `/api` 경로를 백엔드로 프록시하므로 CORS 설정이 필요 없습니다.

### 데이터베이스 연결 실패

```bash
# 데이터베이스 볼륨 삭제 후 재시작
docker-compose down -v
docker-compose up --build
```

### 포트 충돌

- 80: Frontend (Nginx)
- 8000: Backend (FastAPI)
- 5432: PostgreSQL

포트가 이미 사용 중인 경우:
```bash
# 사용 중인 프로세스 확인
lsof -i :80
lsof -i :8000
lsof -i :5432

# 프로세스 종료
kill -9 <PID>
```
