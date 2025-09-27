#!/bin/bash
# scripts/gcp-setup-app.sh
# GCP VM에서 애플리케이션 설정 및 시작 스크립트

set -euo pipefail

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 변수 설정
APP_DIR="/home/ubuntu/cointrader/CoinManagerV2"
DATA_DIR="/home/ubuntu/cointrader/data"
LOGS_DIR="/home/ubuntu/cointrader/logs"

# 애플리케이션 코드 클론 또는 업로드 확인
check_app_code() {
    if [ ! -d "$APP_DIR" ]; then
        log_error "애플리케이션 코드가 없습니다."
        log_info "다음 중 하나를 선택하세요:"
        echo "1. Git clone: git clone <repository-url> $APP_DIR"
        echo "2. 파일 업로드: scp 또는 rsync로 코드 업로드"
        echo "3. 현재 디렉토리에서 복사: cp -r . $APP_DIR"
        exit 1
    fi
    
    log_info "애플리케이션 코드 확인됨: $APP_DIR"
}

# 환경 설정 파일 생성
setup_environment() {
    log_info "환경 설정 파일 생성 중..."
    
    cd "$APP_DIR"
    
    # .env 파일이 없으면 생성
    if [ ! -f ".env" ]; then
        cp .env.example .env
        
        # GCP VM용 기본 설정 적용
        cat > .env << 'EOF'
# ==============================================
# GCP VM 배포용 환경 설정
# ==============================================

# 환경 설정
ENVIRONMENT=production
DEBUG=false

# API 서버 설정
API_HOST=0.0.0.0
API_PORT=8000

# 데이터베이스 설정 (SQLite - VM 내장)
DATABASE_URL=sqlite:////home/ubuntu/cointrader/data/trading.db

# 거래 설정 (모의거래로 시작)
TRADING_ENABLED=true
TRADING_MODE=paper
DEFAULT_MARKET=KRW-BTC
MIN_ORDER_AMOUNT=5000
MAX_POSITION_SIZE=100000
MAX_CONCURRENT_POSITIONS=3
POSITION_SIZE_PERCENT=10.0
STOP_LOSS_PERCENT=3.0
TAKE_PROFIT_PERCENT=2.0
MAX_DAILY_LOSS=50000

# 스캘핑 전략
SCALPING_ENABLED=true
SCALPING_RSI_OVERSOLD=30
SCALPING_RSI_OVERBOUGHT=70
SCALPING_MIN_VOLUME=1000000
SCALPING_MIN_PROFIT=0.5
SCALPING_MAX_LOSS=0.3

# CORS 설정 (Nginx 프록시 고려)
ALLOWED_ORIGINS=["http://localhost:3000","https://your-domain.com"]

# 로깅 설정
LOG_LEVEL=INFO
LOG_FILE=/home/ubuntu/cointrader/logs/trading.log

# 텔레그램 설정 (실제 값으로 변경 필요)
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
TELEGRAM_NOTIFICATIONS_ENABLED=true
NOTIFICATION_TRADE_ALERTS=true
NOTIFICATION_ERROR_ALERTS=true
NOTIFICATION_DAILY_SUMMARY=true
NOTIFICATION_SYSTEM_STATUS=true

# Upbit API 설정 (실거래 시 필요)
UPBIT_ACCESS_KEY=your_upbit_access_key_here
UPBIT_SECRET_KEY=your_upbit_secret_key_here
UPBIT_SERVER_URL=https://api.upbit.com

# 보안 설정
JWT_SECRET_KEY=your_super_secret_jwt_key_here_change_this
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
ENCRYPTION_KEY=your_32_byte_encryption_key_here_change_this

# 백업 설정
AUTO_BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=6
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/home/ubuntu/cointrader/backups
EOF
        
        log_warn "⚠️  .env 파일이 생성되었습니다. 다음 값들을 실제 값으로 변경해야 합니다:"
        echo "  - TELEGRAM_BOT_TOKEN"
        echo "  - TELEGRAM_CHAT_ID"
        echo "  - UPBIT_ACCESS_KEY (실거래 시)"
        echo "  - UPBIT_SECRET_KEY (실거래 시)"
        echo "  - JWT_SECRET_KEY"
        echo "  - ENCRYPTION_KEY"
        echo ""
        echo "편집: nano .env"
    fi
    
    log_info "환경 설정 완료"
}

# Backend 설정
setup_backend() {
    log_info "Backend 설정 중..."
    
    cd "$APP_DIR/backend"
    
    # Python 가상환경 생성
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        log_info "Python 가상환경 생성 완료"
    fi
    
    # 가상환경 활성화 및 의존성 설치
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 데이터베이스 초기화
    log_info "데이터베이스 초기화 중..."
    
    # 데이터 디렉토리 생성
    mkdir -p "$DATA_DIR"
    
    # SQLite 데이터베이스 초기화 (필요시)
    # python -c "from src.database.connection import init_db; import asyncio; asyncio.run(init_db())"
    
    log_info "Backend 설정 완료"
}

# Frontend 설정
setup_frontend() {
    log_info "Frontend 설정 중..."
    
    cd "$APP_DIR/frontend"
    
    # Node.js 의존성 설치
    npm install
    
    # 프로덕션 빌드
    log_info "Frontend 빌드 중... (시간이 걸릴 수 있습니다)"
    npm run build
    
    log_info "Frontend 설정 완료"
}

# 서비스 시작
start_services() {
    log_info "서비스 시작 중..."
    
    # Supervisor로 서비스 시작
    sudo supervisorctl start cointrader-backend
    sudo supervisorctl start cointrader-frontend
    
    # 서비스 상태 확인
    sleep 5
    
    log_info "서비스 상태 확인 중..."
    sudo supervisorctl status
    
    # 포트 확인
    log_info "포트 바인딩 확인 중..."
    netstat -tlnp | grep -E ':3000|:8000' || true
}

# 방화벽 설정 업데이트 (개발 시에만)
update_firewall_for_dev() {
    read -p "개발 모드로 직접 포트 접근을 허용하시겠습니까? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "개발용 방화벽 규칙 추가 중..."
        sudo ufw allow 3000 comment "Frontend development"
        sudo ufw allow 8000 comment "Backend development"
        log_info "포트 3000, 8000이 외부에서 접근 가능합니다."
    else
        log_info "Nginx 프록시를 통해서만 접근 가능합니다."
    fi
}

# SSL 인증서 설치 (선택사항)
setup_ssl() {
    read -p "도메인이 있고 SSL 인증서를 설치하시겠습니까? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "도메인 이름을 입력하세요: " domain
        
        if [ -n "$domain" ]; then
            log_info "SSL 인증서 설치 중..."
            
            # Nginx 설정에서 도메인 업데이트
            sudo sed -i "s/server_name _;/server_name $domain;/" /etc/nginx/sites-available/cointrader
            sudo nginx -t && sudo systemctl reload nginx
            
            # Let's Encrypt 인증서 설치
            sudo certbot --nginx -d "$domain" --non-interactive --agree-tos --email admin@"$domain"
            
            log_info "SSL 인증서 설치 완료"
        fi
    fi
}

# 상태 확인 및 정보 출력
show_status() {
    log_info "배포 완료! 시스템 정보:"
    echo ""
    echo "═══════════════════════════════════════"
    echo "🖥️  시스템 정보"
    echo "═══════════════════════════════════════"
    echo "VM 내부 IP: $(hostname -I | awk '{print $1}')"
    echo "VM 외부 IP: $(curl -s http://checkip.amazonaws.com/ || echo 'N/A')"
    echo ""
    echo "🌐 접속 정보"
    echo "───────────────────────────────────────"
    echo "웹 대시보드: http://[외부IP]/"
    echo "API 문서:    http://[외부IP]/api/docs"
    echo "API 상태:    http://[외부IP]/api/health"
    echo ""
    echo "📁 주요 경로"
    echo "───────────────────────────────────────"
    echo "애플리케이션: $APP_DIR"
    echo "데이터베이스: $DATA_DIR/trading.db"
    echo "로그:         $LOGS_DIR/"
    echo "백업:         /home/ubuntu/cointrader/backups/"
    echo ""
    echo "🔧 관리 명령어"
    echo "───────────────────────────────────────"
    echo "서비스 상태:   sudo supervisorctl status"
    echo "서비스 재시작: sudo supervisorctl restart cointrader-backend cointrader-frontend"
    echo "로그 확인:     tail -f $LOGS_DIR/trading.log"
    echo "백업 실행:     /home/ubuntu/cointrader/backup.sh"
    echo ""
    echo "⚠️  다음 단계"
    echo "───────────────────────────────────────"
    echo "1. .env 파일에서 실제 API 키 설정"
    echo "2. 텔레그램 봇 토큰 및 채팅 ID 설정"
    echo "3. 모의거래로 시스템 테스트"
    echo "4. 실거래 전환 시 TRADING_MODE=live 설정"
    echo ""
}

# 메인 실행
main() {
    log_info "GCP VM CoinTrader 애플리케이션 설정 시작"
    
    check_app_code
    setup_environment
    setup_backend
    setup_frontend
    start_services
    update_firewall_for_dev
    setup_ssl
    show_status
    
    log_info "애플리케이션 설정 완료! 🚀"
}

main "$@"

