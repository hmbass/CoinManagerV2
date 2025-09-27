#!/bin/bash
# scripts/install-nodejs-gcp.sh
# GCP VM에 Node.js 설치 스크립트

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

# Node.js 설치 상태 확인
check_nodejs() {
    log_info "현재 Node.js 설치 상태 확인 중..."
    
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        log_info "Node.js가 이미 설치되어 있습니다: $node_version"
        
        if command -v npm &> /dev/null; then
            local npm_version=$(npm --version)
            log_info "npm 버전: $npm_version"
        fi
        
        # 버전 확인 (Node.js 18 이상 권장)
        local major_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$major_version" -ge 18 ]; then
            log_info "Node.js 버전이 적절합니다 (v18+)"
            return 0
        else
            log_warn "Node.js 버전이 낮습니다 (현재: v$major_version, 권장: v18+)"
            log_info "최신 버전으로 업데이트를 진행합니다..."
        fi
    else
        log_info "Node.js가 설치되지 않았습니다. 설치를 진행합니다..."
    fi
    
    return 1
}

# 방법 1: NodeSource 저장소를 통한 설치 (권장)
install_nodejs_nodesource() {
    log_info "NodeSource 저장소를 통한 Node.js LTS 설치 중..."
    
    # 시스템 업데이트
    sudo apt update
    
    # 필요한 패키지 설치
    sudo apt install -y curl software-properties-common
    
    # NodeSource GPG 키 추가
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | sudo apt-key add -
    
    # NodeSource 저장소 추가 (LTS 버전)
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    
    # Node.js 설치
    sudo apt install -y nodejs
    
    log_info "Node.js 설치 완료"
}

# 방법 2: Snap을 통한 설치 (대안)
install_nodejs_snap() {
    log_info "Snap을 통한 Node.js 설치 중..."
    
    # Snap 설치 (Ubuntu에는 기본 설치됨)
    if ! command -v snap &> /dev/null; then
        sudo apt update
        sudo apt install -y snapd
    fi
    
    # Node.js 설치
    sudo snap install node --classic
    
    log_info "Node.js 설치 완료 (Snap)"
}

# 방법 3: 수동 바이너리 설치
install_nodejs_manual() {
    log_info "수동 바이너리를 통한 Node.js 설치 중..."
    
    # 최신 LTS 버전 다운로드 (예: v20.x.x)
    local node_version="v20.11.0"
    local node_package="node-${node_version}-linux-x64"
    
    cd /tmp
    
    # 다운로드
    wget https://nodejs.org/dist/${node_version}/${node_package}.tar.xz
    
    # 압축 해제
    tar -xf ${node_package}.tar.xz
    
    # 시스템 경로로 이동
    sudo mv ${node_package} /opt/nodejs
    
    # 심볼릭 링크 생성
    sudo ln -sf /opt/nodejs/bin/node /usr/local/bin/node
    sudo ln -sf /opt/nodejs/bin/npm /usr/local/bin/npm
    sudo ln -sf /opt/nodejs/bin/npx /usr/local/bin/npx
    
    # 정리
    rm -f ${node_package}.tar.xz
    
    log_info "Node.js 수동 설치 완료"
}

# npm 업데이트
update_npm() {
    log_info "npm을 최신 버전으로 업데이트 중..."
    
    # npm 자체 업데이트
    sudo npm install -g npm@latest
    
    log_info "npm 업데이트 완료"
}

# 설치 검증
verify_installation() {
    log_info "설치 검증 중..."
    
    if command -v node &> /dev/null && command -v npm &> /dev/null; then
        local node_version=$(node --version)
        local npm_version=$(npm --version)
        
        log_info "✅ Node.js 설치 성공: $node_version"
        log_info "✅ npm 설치 성공: $npm_version"
        
        # 권한 확인
        if npm config get prefix &> /dev/null; then
            log_info "✅ npm 설정 정상"
        else
            log_warn "npm 설정에 문제가 있을 수 있습니다"
        fi
        
        return 0
    else
        log_error "❌ Node.js 설치 실패"
        return 1
    fi
}

# 권한 문제 해결
fix_npm_permissions() {
    log_info "npm 권한 문제 해결 중..."
    
    # npm 글로벌 디렉토리를 홈 디렉토리로 변경
    mkdir -p ~/.npm-global
    npm config set prefix '~/.npm-global'
    
    # PATH에 추가 (bashrc에 영구 저장)
    if ! grep -q "npm-global" ~/.bashrc; then
        echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
        log_info "PATH에 npm 글로벌 경로 추가됨"
    fi
    
    # 현재 세션에 적용
    export PATH=~/.npm-global/bin:$PATH
    
    log_info "npm 권한 설정 완료"
}

# Frontend 의존성 설치
install_frontend_dependencies() {
    log_info "Frontend 의존성 설치 중..."
    
    if [ -d "~/CoinManagerV2/frontend" ]; then
        cd ~/CoinManagerV2/frontend
        
        log_info "package.json 확인 중..."
        if [ -f "package.json" ]; then
            npm install
            log_info "✅ Frontend 의존성 설치 완료"
        else
            log_error "package.json 파일을 찾을 수 없습니다"
            return 1
        fi
    else
        log_error "Frontend 디렉토리를 찾을 수 없습니다"
        return 1
    fi
}

# 메인 실행 함수
main() {
    log_info "GCP VM Node.js 설치 시작"
    
    # 현재 상태 확인
    if check_nodejs; then
        log_info "Node.js가 이미 적절히 설치되어 있습니다"
    else
        # 설치 방법 선택
        echo ""
        echo "Node.js 설치 방법을 선택하세요:"
        echo "1) NodeSource 저장소 (권장)"
        echo "2) Snap 패키지"
        echo "3) 수동 바이너리 설치"
        echo "4) 자동 선택 (NodeSource)"
        echo ""
        
        read -p "선택 (1-4, 기본값: 4): " choice
        choice=${choice:-4}
        
        case $choice in
            1)
                install_nodejs_nodesource
                ;;
            2)
                install_nodejs_snap
                ;;
            3)
                install_nodejs_manual
                ;;
            4|*)
                log_info "자동으로 NodeSource 방법을 선택합니다"
                install_nodejs_nodesource
                ;;
        esac
        
        # npm 업데이트
        update_npm
        
        # 권한 문제 해결
        fix_npm_permissions
        
        # 설치 검증
        if ! verify_installation; then
            log_error "Node.js 설치에 실패했습니다"
            exit 1
        fi
    fi
    
    # Frontend 의존성 설치
    install_frontend_dependencies
    
    log_info "🎉 모든 설치가 완료되었습니다!"
    echo ""
    echo "다음 명령어로 설치를 확인하세요:"
    echo "  node --version"
    echo "  npm --version"
    echo ""
    echo "새 터미널 세션에서 PATH가 적용되도록 다음을 실행하세요:"
    echo "  source ~/.bashrc"
    echo ""
    echo "또는 현재 세션에서 바로 적용:"
    echo "  export PATH=~/.npm-global/bin:$PATH"
}

# 스크립트 실행
main "$@"
