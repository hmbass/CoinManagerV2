#!/bin/bash
# scripts/setup.sh
# CoinTrader 프로젝트 초기 설정 스크립트

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

setup_python_environment() {
    log_message "Python 환경 설정 중..."
    
    cd "$PROJECT_ROOT/backend"
    
    # 가상환경 생성
    if [ ! -d ".venv" ]; then
        log_message "Python 가상환경 생성 중..."
        python3 -m venv .venv
    fi
    
    # 가상환경 활성화
    source .venv/bin/activate
    
    # pip 업그레이드
    pip install --upgrade pip
    
    # 의존성 설치
    log_message "Python 의존성 설치 중..."
    pip install -r requirements.txt
    
    log_message "Python 환경 설정 완료"
}

setup_frontend_environment() {
    log_message "Frontend 환경 설정 중..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Node.js 버전 확인
    if command -v node >/dev/null 2>&1; then
        node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$node_version" -lt 18 ]; then
            log_message "경고: Node.js 18 이상이 권장됩니다. 현재 버전: $(node --version)"
        fi
    else
        log_message "오류: Node.js가 설치되지 않았습니다."
        return 1
    fi
    
    # 의존성 설치
    log_message "Frontend 의존성 설치 중..."
    npm install
    
    log_message "Frontend 환경 설정 완료"
}

setup_environment_file() {
    log_message "환경 파일 설정 중..."
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_message ".env 파일을 생성합니다."
        cat > "$PROJECT_ROOT/.env" << 'EOF'
# 🔑 필수 API 인증 정보
UPBIT_ACCESS_KEY=your_upbit_access_key_here
UPBIT_SECRET_KEY=your_upbit_secret_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# 💰 거래 설정
TRADING_ENABLED=true
TRADING_MODE=paper
DEFAULT_MARKET=KRW-BTC
MIN_ORDER_AMOUNT=5000
MAX_POSITION_SIZE=100000
STOP_LOSS_PERCENT=3.0
TAKE_PROFIT_PERCENT=2.0

# 🗄️ 데이터베이스
DATABASE_URL=sqlite:///./trading.db

# 🌐 API 서버
API_HOST=localhost
API_PORT=8000
ALLOWED_ORIGINS=["http://localhost:3000"]

# 📋 로깅
LOG_LEVEL=INFO
LOG_FILE=logs/trading.log

# 🔒 보안
JWT_SECRET_KEY=your_super_secret_jwt_key_here
ENCRYPTION_KEY=your_32_byte_encryption_key_here

# 📱 알림 설정
TELEGRAM_NOTIFICATIONS_ENABLED=true
NOTIFICATION_TRADE_ALERTS=true

# 🧪 개발 설정
ENVIRONMENT=development
DEBUG_MODE=true
MOCK_UPBIT_API=false
EOF
        log_message "⚠️  .env 파일을 편집하여 실제 값으로 설정하세요!"
    else
        log_message ".env 파일이 이미 존재합니다."
    fi
}

setup_directories() {
    log_message "프로젝트 디렉토리 구조 생성 중..."
    
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/pids"
    mkdir -p "$PROJECT_ROOT/backups"
    mkdir -p "$PROJECT_ROOT/data"
    
    log_message "디렉토리 구조 생성 완료"
}

setup_scripts_permissions() {
    log_message "스크립트 실행 권한 설정 중..."
    
    chmod +x "$PROJECT_ROOT/scripts/server-manager.sh"
    chmod +x "$PROJECT_ROOT/scripts/setup.sh"
    
    log_message "스크립트 실행 권한 설정 완료"
}

main() {
    log_message "CoinTrader 프로젝트 초기 설정 시작"
    
    setup_directories
    setup_scripts_permissions
    setup_environment_file
    setup_python_environment
    setup_frontend_environment
    
    log_message "초기 설정 완료!"
    log_message ""
    log_message "다음 단계:"
    log_message "1. .env 파일을 편집하여 API 키 등을 설정하세요"
    log_message "2. ./scripts/server-manager.sh start 명령으로 서버를 시작하세요"
    log_message "3. http://localhost:3000에서 웹 대시보드에 접속하세요"
}

main "$@"

