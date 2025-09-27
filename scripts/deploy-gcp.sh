#!/bin/bash
# scripts/deploy-gcp.sh
# GCP VM에 CoinTrader 시스템 배포 스크립트

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

# 시스템 업데이트 및 기본 패키지 설치
install_system_dependencies() {
    log_info "시스템 패키지 업데이트 및 설치 중..."
    
    sudo apt update && sudo apt upgrade -y
    
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nodejs \
        npm \
        git \
        curl \
        wget \
        unzip \
        htop \
        nginx \
        certbot \
        python3-certbot-nginx \
        sqlite3 \
        supervisor \
        ufw
    
    log_info "시스템 패키지 설치 완료"
}

# Node.js 최신 버전 설치
install_nodejs() {
    log_info "Node.js LTS 설치 중..."
    
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    # npm 최신 버전 업데이트
    sudo npm install -g npm@latest
    
    log_info "Node.js $(node --version) 설치 완료"
}

# 애플리케이션 디렉토리 설정
setup_app_directory() {
    log_info "애플리케이션 디렉토리 설정 중..."
    
    # 홈 디렉토리에 애플리케이션 폴더 생성
    mkdir -p /home/ubuntu/cointrader/{data,logs,backups,ssl}
    
    # 권한 설정
    chown -R ubuntu:ubuntu /home/ubuntu/cointrader
    
    log_info "애플리케이션 디렉토리 설정 완료"
}

# 방화벽 설정
setup_firewall() {
    log_info "방화벽 설정 중..."
    
    # UFW 기본 정책
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # 필요한 포트 개방
    sudo ufw allow ssh
    sudo ufw allow 80    # HTTP
    sudo ufw allow 443   # HTTPS
    sudo ufw allow 3000  # Frontend (개발 시)
    sudo ufw allow 8000  # Backend (개발 시)
    
    # 방화벽 활성화
    sudo ufw --force enable
    
    log_info "방화벽 설정 완료"
}

# Nginx 설정
setup_nginx() {
    log_info "Nginx 설정 중..."
    
    # 기본 설정 백업
    sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
    
    # CoinTrader 설정 파일 생성
    sudo tee /etc/nginx/sites-available/cointrader << 'EOF'
server {
    listen 80;
    server_name _;  # 도메인이 있으면 여기에 입력
    
    # Frontend (Next.js)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Static files
    location /static/ {
        alias /home/ubuntu/cointrader/CoinManagerV2/frontend/.next/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    # 사이트 활성화
    sudo ln -sf /etc/nginx/sites-available/cointrader /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Nginx 설정 테스트 및 재시작
    sudo nginx -t
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    log_info "Nginx 설정 완료"
}

# Supervisor 설정 (프로세스 관리)
setup_supervisor() {
    log_info "Supervisor 설정 중..."
    
    # Backend 서비스 설정
    sudo tee /etc/supervisor/conf.d/cointrader-backend.conf << 'EOF'
[program:cointrader-backend]
command=/home/ubuntu/cointrader/CoinManagerV2/backend/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
directory=/home/ubuntu/cointrader/CoinManagerV2/backend
user=ubuntu
autostart=true
autorestart=true
stdout_logfile=/home/ubuntu/cointrader/logs/backend-supervisor.log
stderr_logfile=/home/ubuntu/cointrader/logs/backend-supervisor-error.log
environment=PATH="/home/ubuntu/cointrader/CoinManagerV2/backend/.venv/bin"
EOF
    
    # Frontend 서비스 설정
    sudo tee /etc/supervisor/conf.d/cointrader-frontend.conf << 'EOF'
[program:cointrader-frontend]
command=/usr/bin/npm start
directory=/home/ubuntu/cointrader/CoinManagerV2/frontend
user=ubuntu
autostart=true
autorestart=true
stdout_logfile=/home/ubuntu/cointrader/logs/frontend-supervisor.log
stderr_logfile=/home/ubuntu/cointrader/logs/frontend-supervisor-error.log
environment=NODE_ENV="production"
EOF
    
    # Supervisor 재로드
    sudo supervisorctl reread
    sudo supervisorctl update
    
    log_info "Supervisor 설정 완료"
}

# 자동 백업 스크립트 설정
setup_backup() {
    log_info "자동 백업 설정 중..."
    
    # 백업 스크립트 생성
    cat > /home/ubuntu/cointrader/backup.sh << 'EOF'
#!/bin/bash
# 자동 백업 스크립트

BACKUP_DIR="/home/ubuntu/cointrader/backups"
DB_FILE="/home/ubuntu/cointrader/data/trading.db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 데이터베이스 백업
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_DIR/trading_${TIMESTAMP}.db"
    
    # 7일 이상 된 백업 파일 삭제
    find "$BACKUP_DIR" -name "trading_*.db" -mtime +7 -delete
    
    echo "$(date): 백업 완료 - trading_${TIMESTAMP}.db"
fi

# 로그 파일 백업 (압축)
tar -czf "$BACKUP_DIR/logs_${TIMESTAMP}.tar.gz" -C /home/ubuntu/cointrader/logs . 2>/dev/null || true

# 14일 이상 된 로그 백업 삭제
find "$BACKUP_DIR" -name "logs_*.tar.gz" -mtime +14 -delete
EOF
    
    chmod +x /home/ubuntu/cointrader/backup.sh
    
    # Cron 작업 추가 (매일 새벽 3시)
    (crontab -l 2>/dev/null; echo "0 3 * * * /home/ubuntu/cointrader/backup.sh >> /home/ubuntu/cointrader/logs/backup.log 2>&1") | crontab -
    
    log_info "자동 백업 설정 완료"
}

# 시스템 모니터링 설정
setup_monitoring() {
    log_info "모니터링 설정 중..."
    
    # 시스템 상태 확인 스크립트
    cat > /home/ubuntu/cointrader/monitor.sh << 'EOF'
#!/bin/bash
# 시스템 모니터링 스크립트

LOG_FILE="/home/ubuntu/cointrader/logs/monitor.log"

echo "$(date): 시스템 상태 확인" >> "$LOG_FILE"

# 디스크 사용량 확인 (80% 이상 시 경고)
DISK_USAGE=$(df /home | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "$(date): 경고 - 디스크 사용량 ${DISK_USAGE}%" >> "$LOG_FILE"
fi

# 메모리 사용량 확인
MEMORY_USAGE=$(free | awk 'FNR==2{printf "%.0f", $3/$2*100}')
if [ "$MEMORY_USAGE" -gt 85 ]; then
    echo "$(date): 경고 - 메모리 사용량 ${MEMORY_USAGE}%" >> "$LOG_FILE"
fi

# 프로세스 상태 확인
if ! pgrep -f "uvicorn" > /dev/null; then
    echo "$(date): 오류 - Backend 프로세스 중지됨" >> "$LOG_FILE"
fi

if ! pgrep -f "npm start" > /dev/null; then
    echo "$(date): 오류 - Frontend 프로세스 중지됨" >> "$LOG_FILE"
fi
EOF
    
    chmod +x /home/ubuntu/cointrader/monitor.sh
    
    # 5분마다 모니터링 실행
    (crontab -l 2>/dev/null; echo "*/5 * * * * /home/ubuntu/cointrader/monitor.sh") | crontab -
    
    log_info "모니터링 설정 완료"
}

# 메인 실행
main() {
    log_info "GCP VM CoinTrader 배포 시작"
    
    install_system_dependencies
    install_nodejs
    setup_app_directory
    setup_firewall
    setup_nginx
    setup_supervisor
    setup_backup
    setup_monitoring
    
    log_info "GCP VM 배포 완료!"
    echo ""
    echo "다음 단계:"
    echo "1. 애플리케이션 코드 배포: git clone 또는 파일 업로드"
    echo "2. 환경 설정: .env 파일 설정"
    echo "3. 애플리케이션 빌드 및 시작"
    echo "4. Nginx에서 도메인 설정 (선택사항)"
    echo "5. SSL 인증서 설치 (선택사항)"
}

main "$@"

