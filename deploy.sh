#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
#  WHALEGOD Deploy Script
#  wen whale moves, we move first ser.
#
#  Usage:
#    ./deploy.sh              Deploy with Docker (default)
#    ./deploy.sh --bare       Deploy without Docker (bare-metal + systemd)
#    ./deploy.sh --systemd    Install systemd service only
#    ./deploy.sh --stop       Stop the bot
#    ./deploy.sh --logs       Show live logs
#    ./deploy.sh --status     Check bot status
# ============================================================================

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="whalegod"

banner() {
    echo -e "${CYAN}${BOLD}"
    echo "  ============================================"
    echo "         WHALEGOD DEPLOYER v1.0"
    echo "     wen whale moves, we move first ser."
    echo "  ============================================"
    echo -e "${RESET}"
}

# ---------------------------------------------------------------------------
# Check .env
# ---------------------------------------------------------------------------
check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}[!] .env file not found${RESET}"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${YELLOW}[i] Created .env from .env.example${RESET}"
            echo -e "${RED}[!] Edit .env with your API keys before deploying!${RESET}"
            echo ""
            echo -e "    Required keys:"
            echo -e "    ${CYAN}TELEGRAM_BOT_TOKEN${RESET}  - from @BotFather"
            echo -e "    ${CYAN}HELIUS_API_KEY${RESET}      - free at helius.dev"
            echo -e "    ${CYAN}ALCHEMY_API_KEY${RESET}     - free at alchemy.com"
            echo -e "    ${CYAN}ETHERSCAN_API_KEY${RESET}   - free at etherscan.io/apis"
            echo ""
            echo -e "    Edit with:  ${BOLD}nano .env${RESET}"
            exit 1
        else
            echo -e "${RED}[!] .env.example not found — cannot continue${RESET}"
            exit 1
        fi
    fi

    # Validate required vars
    local missing=()
    for var in TELEGRAM_BOT_TOKEN HELIUS_API_KEY ALCHEMY_API_KEY ETHERSCAN_API_KEY; do
        val=$(grep "^${var}=" .env | cut -d= -f2-)
        if [ -z "$val" ]; then
            missing+=("$var")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}[!] Missing required values in .env:${RESET}"
        for v in "${missing[@]}"; do
            echo -e "    ${YELLOW}- $v${RESET}"
        done
        echo ""
        echo -e "    Edit with:  ${BOLD}nano .env${RESET}"
        exit 1
    fi

    echo -e "${GREEN}[+] .env validated${RESET}"
}

# ---------------------------------------------------------------------------
# Docker deploy
# ---------------------------------------------------------------------------
deploy_docker() {
    banner
    check_env

    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}[*] Docker not found — installing...${RESET}"
        curl -fsSL https://get.docker.com | sh
        echo -e "${GREEN}[+] Docker installed${RESET}"
    fi

    # Detect compose command
    local COMPOSE_CMD=""
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        echo -e "${RED}[!] Docker Compose not found${RESET}"
        echo -e "    Install: https://docs.docker.com/compose/install/"
        exit 1
    fi

    echo -e "${GREEN}[+] Using: ${COMPOSE_CMD}${RESET}"

    echo -e "${CYAN}[*] Building WHALEGOD...${RESET}"
    $COMPOSE_CMD build --no-cache

    echo -e "${CYAN}[*] Stopping old container...${RESET}"
    $COMPOSE_CMD down 2>/dev/null || true

    echo -e "${CYAN}[*] Starting WHALEGOD...${RESET}"
    $COMPOSE_CMD up -d

    echo -e "${CYAN}[*] Waiting for startup...${RESET}"
    sleep 5

    if $COMPOSE_CMD ps | grep -q "whalegod-bot"; then
        local STATUS
        STATUS=$(docker inspect --format='{{.State.Status}}' whalegod-bot 2>/dev/null || echo "unknown")
        if [ "$STATUS" = "running" ]; then
            echo -e "${GREEN}${BOLD}"
            echo "  ============================================"
            echo "     WHALEGOD IS LIVE SER"
            echo "     wagmi, the ocean awaits!"
            echo "  ============================================"
            echo -e "${RESET}"
            echo -e "  ${CYAN}Logs:${RESET}     $COMPOSE_CMD logs -f whalegod"
            echo -e "  ${CYAN}Restart:${RESET}  $COMPOSE_CMD restart whalegod"
            echo -e "  ${CYAN}Stop:${RESET}     $COMPOSE_CMD down"
            echo -e "  ${CYAN}Health:${RESET}   curl http://localhost:8080/health"
        else
            echo -e "${YELLOW}[!] Container status: ${STATUS}${RESET}"
            echo -e "    Check logs: $COMPOSE_CMD logs whalegod"
        fi
    else
        echo -e "${RED}[!] Container not running${RESET}"
        echo -e "    Check logs: $COMPOSE_CMD logs whalegod"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Bare-metal deploy (no Docker)
# ---------------------------------------------------------------------------
deploy_bare() {
    banner
    check_env

    echo -e "${CYAN}[*] Setting up bare-metal deployment...${RESET}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}[!] Python 3 not found. Install Python 3.11+${RESET}"
        exit 1
    fi

    local PY_VER
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo -e "${GREEN}[+] Python ${PY_VER} found${RESET}"

    # Create venv
    if [ ! -d "venv" ]; then
        echo -e "${CYAN}[*] Creating virtual environment...${RESET}"
        python3 -m venv venv
    fi

    echo -e "${CYAN}[*] Installing dependencies...${RESET}"
    venv/bin/pip install --upgrade pip -q
    venv/bin/pip install -r requirements.txt -q
    echo -e "${GREEN}[+] Dependencies installed${RESET}"

    # Create data dir
    mkdir -p data

    # Install systemd service
    install_systemd

    echo -e "${CYAN}[*] Starting WHALEGOD service...${RESET}"
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    sudo systemctl restart $SERVICE_NAME

    sleep 3

    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}${BOLD}"
        echo "  ============================================"
        echo "     WHALEGOD IS LIVE SER"
        echo "     wagmi, the ocean awaits!"
        echo "  ============================================"
        echo -e "${RESET}"
        echo -e "  ${CYAN}Logs:${RESET}     sudo journalctl -u $SERVICE_NAME -f"
        echo -e "  ${CYAN}Restart:${RESET}  sudo systemctl restart $SERVICE_NAME"
        echo -e "  ${CYAN}Stop:${RESET}     sudo systemctl stop $SERVICE_NAME"
        echo -e "  ${CYAN}Status:${RESET}   sudo systemctl status $SERVICE_NAME"
        echo -e "  ${CYAN}Health:${RESET}   curl http://localhost:8080/health"
    else
        echo -e "${RED}[!] Service failed to start${RESET}"
        echo -e "    Check logs: sudo journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Systemd service installer
# ---------------------------------------------------------------------------
install_systemd() {
    local SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    local WORK_DIR="$SCRIPT_DIR"
    local PYTHON_BIN="${WORK_DIR}/venv/bin/python"
    local CURRENT_USER
    CURRENT_USER=$(whoami)

    echo -e "${CYAN}[*] Installing systemd service...${RESET}"

    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=WHALEGOD Whale Tracker Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
Group=${CURRENT_USER}
WorkingDirectory=${WORK_DIR}
EnvironmentFile=${WORK_DIR}/.env
ExecStart=${PYTHON_BIN} -m bot.main
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${WORK_DIR}/data
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}[+] Systemd service installed at ${SERVICE_FILE}${RESET}"
}

# ---------------------------------------------------------------------------
# Utility commands
# ---------------------------------------------------------------------------
stop_bot() {
    echo -e "${CYAN}[*] Stopping WHALEGOD...${RESET}"

    # Try Docker first
    if command -v docker &> /dev/null; then
        if docker compose version &> /dev/null 2>&1; then
            docker compose down 2>/dev/null && echo -e "${GREEN}[+] Docker container stopped${RESET}" && return
        elif command -v docker-compose &> /dev/null 2>&1; then
            docker-compose down 2>/dev/null && echo -e "${GREEN}[+] Docker container stopped${RESET}" && return
        fi
    fi

    # Try systemd
    if sudo systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
        sudo systemctl stop $SERVICE_NAME
        echo -e "${GREEN}[+] Systemd service stopped${RESET}"
        return
    fi

    echo -e "${YELLOW}[!] No running WHALEGOD instance found${RESET}"
}

show_logs() {
    # Try Docker first
    if command -v docker &> /dev/null && docker ps --filter name=whalegod-bot --format '{{.Names}}' | grep -q whalegod-bot; then
        if docker compose version &> /dev/null 2>&1; then
            docker compose logs -f whalegod
        else
            docker-compose logs -f whalegod
        fi
        return
    fi

    # Fallback to systemd
    sudo journalctl -u $SERVICE_NAME -f
}

show_status() {
    echo -e "${CYAN}[*] WHALEGOD Status${RESET}"
    echo ""

    # Docker check
    if command -v docker &> /dev/null && docker ps --filter name=whalegod-bot --format '{{.Names}}' | grep -q whalegod-bot; then
        echo -e "${GREEN}[Docker] Container is RUNNING${RESET}"
        docker ps --filter name=whalegod-bot --format "table {{.Status}}\t{{.Ports}}"
    elif sudo systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
        echo -e "${GREEN}[Systemd] Service is RUNNING${RESET}"
        sudo systemctl status $SERVICE_NAME --no-pager -l | head -20
    else
        echo -e "${RED}[!] WHALEGOD is NOT running${RESET}"
        return
    fi

    echo ""
    # Health check
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}[Health] OK${RESET}"
        curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8080/health
    else
        echo -e "${YELLOW}[Health] Endpoint not responding yet${RESET}"
    fi
}

# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------
case "${1:-}" in
    --bare)
        deploy_bare
        ;;
    --systemd)
        banner
        install_systemd
        echo -e "${YELLOW}[i] Run 'sudo systemctl daemon-reload && sudo systemctl enable --now $SERVICE_NAME'${RESET}"
        ;;
    --stop)
        stop_bot
        ;;
    --logs)
        show_logs
        ;;
    --status)
        show_status
        ;;
    --help|-h)
        echo "WHALEGOD Deploy Script"
        echo ""
        echo "Usage:"
        echo "  ./deploy.sh              Deploy with Docker (default)"
        echo "  ./deploy.sh --bare       Deploy without Docker (Python + systemd)"
        echo "  ./deploy.sh --systemd    Install systemd service only"
        echo "  ./deploy.sh --stop       Stop the bot"
        echo "  ./deploy.sh --logs       Show live logs"
        echo "  ./deploy.sh --status     Check bot status"
        echo "  ./deploy.sh --help       Show this help"
        ;;
    *)
        deploy_docker
        ;;
esac
