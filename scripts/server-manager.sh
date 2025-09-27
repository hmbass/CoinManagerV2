#!/bin/bash
# scripts/server-manager.sh
# CoinTrader 통합 서버 관리 스크립트

set -euo pipefail

# ==============================================
# 설정 및 상수
# ==============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_ROOT/logs"
PIDS_DIR="$PROJECT_ROOT/pids"

# 포트 설정
FRONTEND_PORT=3000
BACKEND_PORT=8000
WEBSOCKET_PORT=8001

# PID 파일
FRONTEND_PID_FILE="$PIDS_DIR/frontend.pid"
BACKEND_PID_FILE="$PIDS_DIR/backend.pid"

# 로그 파일
FRONTEND_LOG="$LOGS_DIR/frontend.log"
BACKEND_LOG="$LOGS_DIR/backend.log"
SYSTEM_LOG="$LOGS_DIR/system.log"
ERROR_LOG="$LOGS_DIR/errors.log"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================
# 유틸리티 함수
# ==============================================

log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # 색상 설정
    local color=""
    case $level in
        "INFO")  color=$GREEN ;;
        "WARN")  color=$YELLOW ;;
        "ERROR") color=$RED ;;
        "DEBUG") color=$BLUE ;;
        *)       color=$NC ;;
    esac
    
    # 콘솔 출력
    echo -e "${color}[$timestamp] [$level] $message${NC}"
    
    # 파일 로깅
    echo "[$timestamp] [$level] $message" >> "$SYSTEM_LOG"
    
    # 오류인 경우 오류 로그에도 기록
    if [ "$level" = "ERROR" ]; then
        echo "[$timestamp] [$level] $message" >> "$ERROR_LOG"
    fi
}

create_directories() {
    mkdir -p "$LOGS_DIR" "$PIDS_DIR"
    log_message "INFO" "디렉토리 구조 생성 완료"
}

stop_service_by_pid() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log_message "INFO" "$service_name (PID: $pid) 중지 중..."
            kill -TERM "$pid" 2>/dev/null || true
            
            # 최대 10초 대기
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # 여전히 실행 중이면 강제 종료
            if kill -0 "$pid" 2>/dev/null; then
                log_message "WARN" "$service_name 강제 종료 중..."
                kill -KILL "$pid" 2>/dev/null || true
                sleep 1
            fi
            
            log_message "INFO" "$service_name 중지 완료"
        fi
        
        rm -f "$pid_file"
    fi
}

check_service_status() {
    local pid_file=$1
    local service_name=$2
    local port=$3
    
    local status="❌ 중지됨"
    local color=$RED
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            # 포트 체크
            if netstat -an 2>/dev/null | grep ":$port.*LISTEN" > /dev/null 2>&1; then
                status="✅ 실행 중 (PID: $pid, Port: $port)"
                color=$GREEN
            else
                status="⚠️  프로세스 실행 중이나 포트 바인딩 실패 (PID: $pid)"
                color=$YELLOW
            fi
        else
            rm -f "$pid_file"
        fi
    fi
    
    printf "  %-15s: %b%s%b\n" "$service_name" "$color" "$status" "$NC"
}

# ==============================================
# 서비스 시작 함수
# ==============================================

start_backend() {
    log_message "INFO" "Backend 시작 중..."
    
    cd "$PROJECT_ROOT/backend"
    
    # 가상환경 활성화
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        log_message "INFO" "Python 가상환경 활성화됨"
    else
        log_message "ERROR" "Python 가상환경이 없습니다. setup.sh를 실행하세요."
        return 1
    fi
    
    # 서버 시작
    nohup uvicorn src.main:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        > "$BACKEND_LOG" 2>&1 &
    
    echo $! > "$BACKEND_PID_FILE"
    sleep 3
    
    log_message "INFO" "Backend 시작 완료 (포트: $BACKEND_PORT)"
}

start_frontend() {
    log_message "INFO" "Frontend 시작 중..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # 의존성 설치 확인
    if [ ! -d "node_modules" ]; then
        log_message "INFO" "Frontend 의존성 설치 중..."
        npm install
    fi
    
    # 개발 모드로 시작
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    
    echo $! > "$FRONTEND_PID_FILE"
    sleep 3
    
    log_message "INFO" "Frontend 시작 완료 (포트: $FRONTEND_PORT)"
}

# ==============================================
# 메인 명령어 함수들
# ==============================================

start_all_services() {
    log_message "INFO" "=== CoinTrader 시스템 시작 ==="
    
    create_directories
    
    # 서비스 시작 순서
    start_backend
    start_frontend
    
    log_message "INFO" "=== 모든 서비스 시작 완료 ==="
    show_status
}

stop_all_services() {
    log_message "INFO" "=== CoinTrader 시스템 중지 ==="
    
    stop_service_by_pid "$FRONTEND_PID_FILE" "Frontend"
    stop_service_by_pid "$BACKEND_PID_FILE" "Backend"
    
    log_message "INFO" "=== 모든 서비스 중지 완료 ==="
}

restart_all_services() {
    log_message "INFO" "=== CoinTrader 시스템 재시작 ==="
    stop_all_services
    sleep 3
    start_all_services
}

show_status() {
    echo ""
    log_message "INFO" "=== CoinTrader 시스템 상태 ==="
    echo ""
    
    check_service_status "$FRONTEND_PID_FILE" "Frontend" "$FRONTEND_PORT"
    check_service_status "$BACKEND_PID_FILE" "Backend" "$BACKEND_PORT"
    
    echo ""
    log_message "INFO" "서비스 URL:"
    echo "  Frontend:  http://localhost:$FRONTEND_PORT"
    echo "  Backend:   http://localhost:$BACKEND_PORT"
    echo "  API Docs:  http://localhost:$BACKEND_PORT/docs"
    echo ""
}

show_logs() {
    local service=$1
    
    case $service in
        "frontend"|"fe")
            log_message "INFO" "Frontend 로그 모니터링 시작 (Ctrl+C로 종료)"
            tail -f "$FRONTEND_LOG"
            ;;
        "backend"|"be")
            log_message "INFO" "Backend 로그 모니터링 시작 (Ctrl+C로 종료)"
            tail -f "$BACKEND_LOG"
            ;;
        "system"|"all"|"")
            log_message "INFO" "시스템 로그 모니터링 시작 (Ctrl+C로 종료)"
            tail -f "$SYSTEM_LOG"
            ;;
        *)
            log_message "ERROR" "지원되지 않는 로그 타입: $service"
            echo "사용법: $0 logs [frontend|backend|system]"
            ;;
    esac
}

show_help() {
    echo "CoinTrader 서버 관리 스크립트"
    echo ""
    echo "사용법: $0 <명령어> [옵션]"
    echo ""
    echo "명령어:"
    echo "  start                 모든 서비스 시작"
    echo "  stop                  모든 서비스 중지"
    echo "  restart               모든 서비스 재시작"
    echo "  status                모든 서비스 상태 확인"
    echo "  logs <service>        특정 서비스 로그 모니터링"
    echo ""
    echo "로그 모니터링:"
    echo "  logs frontend         Frontend 로그"
    echo "  logs backend          Backend 로그"
    echo "  logs system           시스템 로그"
    echo ""
    echo "예시:"
    echo "  $0 start              # 모든 서비스 시작"
    echo "  $0 logs backend       # Backend 로그 모니터링"
    echo "  $0 restart            # 모든 서비스 재시작"
}

# ==============================================
# 메인 실행 부분
# ==============================================

case "${1:-}" in
    "start")
        start_all_services
        ;;
    "stop")
        stop_all_services
        ;;
    "restart")
        restart_all_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "${2:-}"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "잘못된 명령어: ${1:-}"
        echo "도움말을 보려면 '$0 help'를 실행하세요."
        exit 1
        ;;
esac

