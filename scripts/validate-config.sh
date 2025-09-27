#!/bin/bash
# scripts/validate-config.sh
# 환경 설정 검증 스크립트

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "CoinTrader 환경 설정 검증 시작"

# .env 파일 존재 확인
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_error ".env 파일이 없습니다."
    log_info ".env.example을 복사하여 .env 파일을 생성하세요:"
    echo "  cp .env.example .env"
    exit 1
fi

log_info ".env 파일 발견됨"

# 환경 변수 로드
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a
fi

# 필수 설정 확인
check_required_vars() {
    local missing_vars=()
    
    # 기본 설정
    [ -z "${ENVIRONMENT:-}" ] && missing_vars+=("ENVIRONMENT")
    [ -z "${API_PORT:-}" ] && missing_vars+=("API_PORT")
    
    # 실거래 모드일 때 필수 설정
    if [ "${TRADING_MODE:-paper}" = "live" ]; then
        [ -z "${UPBIT_ACCESS_KEY:-}" ] || [ "${UPBIT_ACCESS_KEY}" = "your_upbit_access_key_here" ] && missing_vars+=("UPBIT_ACCESS_KEY")
        [ -z "${UPBIT_SECRET_KEY:-}" ] || [ "${UPBIT_SECRET_KEY}" = "your_upbit_secret_key_here" ] && missing_vars+=("UPBIT_SECRET_KEY")
    fi
    
    # 텔레그램 활성화 시 필수 설정
    if [ "${TELEGRAM_ENABLED:-true}" = "true" ]; then
        [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ "${TELEGRAM_BOT_TOKEN}" = "your_telegram_bot_token_here" ] && missing_vars+=("TELEGRAM_BOT_TOKEN")
        [ -z "${TELEGRAM_CHAT_ID:-}" ] || [ "${TELEGRAM_CHAT_ID}" = "your_telegram_chat_id_here" ] && missing_vars+=("TELEGRAM_CHAT_ID")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "다음 환경 변수들이 설정되지 않았습니다:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        return 1
    fi
    
    return 0
}

# 설정 값 검증
validate_config_values() {
    local errors=0
    
    # 포트 번호 검증
    if ! [[ "${API_PORT:-8000}" =~ ^[0-9]+$ ]] || [ "${API_PORT:-8000}" -lt 1 ] || [ "${API_PORT:-8000}" -gt 65535 ]; then
        log_error "API_PORT는 1-65535 사이의 숫자여야 합니다: ${API_PORT:-8000}"
        ((errors++))
    fi
    
    # 거래 모드 검증
    if [ "${TRADING_MODE:-paper}" != "live" ] && [ "${TRADING_MODE:-paper}" != "paper" ]; then
        log_error "TRADING_MODE는 'live' 또는 'paper'여야 합니다: ${TRADING_MODE:-paper}"
        ((errors++))
    fi
    
    # 로그 레벨 검증
    if [[ ! "${LOG_LEVEL:-INFO}" =~ ^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$ ]]; then
        log_error "LOG_LEVEL은 DEBUG, INFO, WARNING, ERROR, CRITICAL 중 하나여야 합니다: ${LOG_LEVEL:-INFO}"
        ((errors++))
    fi
    
    # 환경 검증
    if [[ ! "${ENVIRONMENT:-development}" =~ ^(development|staging|production)$ ]]; then
        log_error "ENVIRONMENT는 development, staging, production 중 하나여야 합니다: ${ENVIRONMENT:-development}"
        ((errors++))
    fi
    
    return $errors
}

# 디렉토리 구조 확인
check_directories() {
    local missing_dirs=()
    
    [ ! -d "$PROJECT_ROOT/logs" ] && missing_dirs+=("logs")
    [ ! -d "$PROJECT_ROOT/pids" ] && missing_dirs+=("pids")
    [ ! -d "$PROJECT_ROOT/backend" ] && missing_dirs+=("backend")
    [ ! -d "$PROJECT_ROOT/frontend" ] && missing_dirs+=("frontend")
    
    if [ ${#missing_dirs[@]} -gt 0 ]; then
        log_warn "다음 디렉토리들이 없습니다 (자동 생성됨):"
        for dir in "${missing_dirs[@]}"; do
            echo "  - $dir"
            mkdir -p "$PROJECT_ROOT/$dir"
        done
    fi
}

# Python 환경 확인
check_python_env() {
    if [ ! -d "$PROJECT_ROOT/backend/.venv" ]; then
        log_warn "Python 가상환경이 없습니다."
        log_info "다음 명령어로 설정하세요:"
        echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        return 1
    fi
    
    log_info "Python 가상환경 확인됨"
    return 0
}

# Node.js 환경 확인
check_nodejs_env() {
    if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
        log_warn "Frontend 의존성이 설치되지 않았습니다."
        log_info "다음 명령어로 설정하세요:"
        echo "  cd frontend && npm install"
        return 1
    fi
    
    log_info "Frontend 의존성 확인됨"
    return 0
}

# 메인 검증 실행
main() {
    local exit_code=0
    
    # 필수 변수 확인
    if ! check_required_vars; then
        exit_code=1
    fi
    
    # 설정 값 검증
    if ! validate_config_values; then
        exit_code=1
    fi
    
    # 디렉토리 구조 확인
    check_directories
    
    # 환경 확인 (경고만)
    check_python_env || true
    check_nodejs_env || true
    
    echo ""
    echo "=== 환경 설정 요약 ==="
    echo "환경: ${ENVIRONMENT:-development}"
    echo "거래 모드: ${TRADING_MODE:-paper}"
    echo "API 포트: ${API_PORT:-8000}"
    echo "텔레그램: ${TELEGRAM_ENABLED:-true}"
    echo "로그 레벨: ${LOG_LEVEL:-INFO}"
    echo ""
    
    if [ $exit_code -eq 0 ]; then
        log_info "✅ 환경 설정 검증 완료"
        log_info "서버를 시작하려면: scripts/server-manager.sh start"
    else
        log_error "❌ 환경 설정에 문제가 있습니다"
        log_info "설정을 수정한 후 다시 검증하세요"
    fi
    
    exit $exit_code
}

main "$@"

