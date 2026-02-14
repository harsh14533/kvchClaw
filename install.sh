#!/bin/bash
# kvchClaw Installer
# One command setup for any Linux machine
# Usage: curl -fsSL https://raw.githubusercontent.com/harsh14533/kvchClaw/main/install.sh | bash

set -e

# Colors
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
BOLD="\033[1m"
RESET="\033[0m"

log() { echo -e "${GREEN}[kvchClaw]${RESET} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${RESET} $1"; }
error() { echo -e "${RED}[ERROR]${RESET} $1"; exit 1; }
header() { echo -e "\n${BOLD}${BLUE}=== $1 ===${RESET}\n"; }

# Banner
echo -e "${BOLD}"
cat << 'EOF'
    __               __       ________
   / /____   _____ / /_     / ____/ /___ ___      __
  / //_/ | | / / ___/ __ \   / /   / / __ `/ | /| / /
 / ,<  | |/ / /__/ / / /  / /___/ / /_/ /| |/ |/ /
/_/|_| |___/\___/_/ /_/   \____/_/\__,_/ |__/|__/

EOF
echo -e "${RESET}"
echo "Personal AI Agent for Linux — One Command Setup"
echo "================================================"
echo ""

# Check Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "kvchClaw only supports Linux. Detected: $OSTYPE"
fi

header "Step 1 — Detecting Your Hardware"

# RAM detection
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
log "RAM detected: ${TOTAL_RAM}GB"

# CPU detection
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
log "CPU detected: $CPU_MODEL"

# Disk space
FREE_DISK=$(df -BG ~ | awk 'NR==2{print $4}' | tr -d 'G')
log "Free disk space: ${FREE_DISK}GB"

# Recommend model based on RAM
if [ "$TOTAL_RAM" -lt 6 ]; then
    RECOMMENDED_MODEL="phi4-mini:3b"
    MODEL_SIZE="2GB"
    warn "Low RAM detected (${TOTAL_RAM}GB). Using lightweight model."
elif [ "$TOTAL_RAM" -lt 12 ]; then
    RECOMMENDED_MODEL="qwen2.5-coder:7b"
    MODEL_SIZE="4.7GB"
    log "Mid range RAM detected. Using balanced model."
else
    RECOMMENDED_MODEL="qwen2.5-coder:7b"
    MODEL_SIZE="4.7GB"
    log "Good RAM detected. Using full model."
fi

log "Recommended local model: $RECOMMENDED_MODEL ($MODEL_SIZE)"

# Check disk space
if [ "$FREE_DISK" -lt 6 ]; then
    warn "Low disk space (${FREE_DISK}GB free). You need at least 6GB."
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        error "Cancelled. Free up disk space and try again."
    fi
fi

header "Step 2 — Installing System Dependencies"

# Detect package manager
if command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    log "Package manager: apt (Ubuntu/Debian)"
    sudo apt update -qq
    sudo apt install -y python3 python3-pip python3-venv curl git ffmpeg scrot xdotool wmctrl sysstat -qq
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    log "Package manager: dnf (Fedora/RHEL)"
    sudo dnf install -y python3 python3-pip curl git ffmpeg scrot xdotool wmctrl sysstat -q
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    log "Package manager: pacman (Arch)"
    sudo pacman -S --noconfirm python python-pip curl git ffmpeg scrot xdotool wmctrl sysstat
else
    warn "Unknown package manager. Make sure python3, pip, git, ffmpeg are installed."
fi

header "Step 3 — Installing Ollama (Local AI)"

if command -v ollama &> /dev/null; then
    log "Ollama already installed"
else
    log "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    log "Ollama installed"
fi

# Enable Ollama service
sudo systemctl enable ollama 2>/dev/null || true
sudo systemctl start ollama 2>/dev/null || true
sleep 2

# Pull recommended model
log "Downloading AI model: $RECOMMENDED_MODEL ($MODEL_SIZE)"
log "This may take 5-15 minutes depending on your internet speed..."
ollama pull $RECOMMENDED_MODEL

header "Step 4 — Setting Up kvchClaw"

INSTALL_DIR="$HOME/kvchClaw"

if [ -d "$INSTALL_DIR" ]; then
    log "kvchClaw folder exists. Updating..."
    cd "$INSTALL_DIR"
    git pull
else
    log "Cloning kvchClaw..."
    git clone https://github.com/harsh14533/kvchClaw.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

log "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

log "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

header "Step 5 — Configuration"

echo ""
echo "You need a Telegram bot to use kvchClaw."
echo "If you don't have one:"
echo "  1. Open Telegram"
echo "  2. Search @BotFather"
echo "  3. Send /newbot"
echo "  4. Follow instructions and copy the token"
echo ""

read -p "Enter your Telegram Bot Token: " TELEGRAM_TOKEN
if [ -z "$TELEGRAM_TOKEN" ]; then
    error "Telegram token is required"
fi

echo ""
echo "Now get your Telegram User ID:"
echo "  1. Open Telegram"
echo "  2. Search @userinfobot"
echo "  3. Send any message"
echo "  4. Copy the ID number it shows you"
echo ""

read -p "Enter your Telegram User ID: " TELEGRAM_USER_ID
if [ -z "$TELEGRAM_USER_ID" ]; then
    error "Telegram user ID is required"
fi

echo ""
echo "Optional but recommended — Free API keys for faster responses:"
echo "  Groq (fastest): https://console.groq.com"
echo "  Gemini: https://aistudio.google.com/apikey"
echo "  Mistral: https://console.mistral.ai"
echo "  (Press Enter to skip any of these)"
echo ""

read -p "Groq API Key (recommended): " GROQ_API_KEY
read -p "Gemini API Key (optional): " GEMINI_API_KEY
read -p "Mistral API Key (optional): " MISTRAL_API_KEY
read -p "GitHub Token (optional): " GITHUB_TOKEN
read -p "GitHub Username (optional): " GITHUB_USERNAME

# Write .env file
cat > "$INSTALL_DIR/.env" << EOF
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
TELEGRAM_USER_ID=$TELEGRAM_USER_ID
GROQ_API_KEY=$GROQ_API_KEY
GEMINI_API_KEY=$GEMINI_API_KEY
MISTRAL_API_KEY=$MISTRAL_API_KEY
GITHUB_TOKEN=$GITHUB_TOKEN
GITHUB_USERNAME=$GITHUB_USERNAME
EOF

log ".env file created"

header "Step 6 — Setting Up Terminal Command"

# Create ask command
sudo tee /usr/local/bin/ask > /dev/null << EOF
#!/bin/bash
cd $INSTALL_DIR
source $INSTALL_DIR/venv/bin/activate
python $INSTALL_DIR/ask.py "\$@"
EOF
sudo chmod +x /usr/local/bin/ask
log "Terminal command 'ask' is ready"

header "Step 7 — Setting Up Auto Start"

USERNAME=$(whoami)

sudo tee /etc/systemd/system/kvclaw.service > /dev/null << EOF
[Unit]
Description=kvchClaw AI Agent Watchdog
After=network.target ollama.service

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/watchdog.sh
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/watchdog.log
StandardError=append:$INSTALL_DIR/watchdog.log

[Install]
WantedBy=multi-user.target
EOF

chmod +x "$INSTALL_DIR/watchdog.sh"
sudo systemctl daemon-reload
sudo systemctl enable kvclaw
sudo systemctl start kvclaw

sleep 3

header "Installation Complete!"

echo ""
echo -e "${GREEN}${BOLD}kvchClaw is now running on your machine!${RESET}"
echo ""
echo "Your setup:"
echo "  RAM: ${TOTAL_RAM}GB"
echo "  Local model: $RECOMMENDED_MODEL"
if [ -n "$GROQ_API_KEY" ]; then
echo "  Groq API: Connected (fast mode)"
else
echo "  Groq API: Not set (using local model only)"
fi
echo ""
echo "How to use:"
echo "  Telegram: Open your bot and send a message"
echo "  Terminal: ask what is my ip address"
echo "  Terminal: ask organize my downloads"
echo "  Terminal: ask why is my pc slow"
echo ""
echo "Check status:"
echo "  sudo systemctl status kvclaw"
echo "  tail -f $INSTALL_DIR/watchdog.log"
echo ""
echo -e "${YELLOW}Give kvchClaw a star on GitHub!${RESET}"
echo "https://github.com/harsh14533/kvchClaw"
echo ""
