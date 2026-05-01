#!/bin/bash
# ============================================================================
# DNK HUB Workspace Initialization Script
# ============================================================================
# This script bootstraps the entire DNK HUB ecosystem.
# It sets up virtual environments, installs dependencies, and verifies structure.
#
# Usage:
#   ./infra/init_workspace.sh
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

# Ensure we are in the project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo -e "${CYAN}🚀 DNK HUB Workspace Initialization${NC}"
echo -e "Root directory: $ROOT_DIR"
echo ""

# 1. Prerequisites Check
echo -e "${CYAN}→${NC} Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 not found. Please install Python 3.11+.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"

# 2. Components Setup

setup_venv() {
    local component_path=$1
    local name=$2
    
    echo -e "\n${CYAN}📦 Setting up $name...${NC}"
    if [ -d "$component_path" ]; then
        cd "$component_path"
        
        # Check if setup script exists
        if [ -f "./setup-hermes.sh" ]; then
            echo -e "${CYAN}→${NC} Running custom setup script..."
            bash ./setup-hermes.sh
        elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
            echo -e "${CYAN}→${NC} Creating venv..."
            python3 -m venv venv
            source venv/bin/activate
            echo -e "${CYAN}→${NC} Installing dependencies..."
            pip install --upgrade pip
            if [ -f "requirements.txt" ]; then
                pip install -r requirements.txt
            fi
            if [ -f "pyproject.toml" ]; then
                pip install -e .
            fi
            deactivate
            echo -e "${GREEN}✓${NC} $name setup complete"
        else
            echo -e "${YELLOW}⚠${NC} No setup path found for $name (skipping venv)"
        fi
        cd "$ROOT_DIR"
    else
        echo -e "${RED}✗ $name directory not found at $component_path${NC}"
    fi
}

# Setup Core Components
setup_venv "core/hermes-agent" "Hermes Agent (Engine)"
setup_venv "core/telegram-bot" "Telegram Bot"
setup_venv "integrations/dnk-git-research" "Git Research Engine"

# 3. Structure Verification
echo -e "\n${CYAN}→${NC} Verifying workspace structure..."

MANDATORY_DIRS=("infra" "core" "memory/vault" "docs")
for dir in "${MANDATORY_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $dir/ found"
    else
        echo -e "${RED}✗ $dir/ missing!${NC}"
    fi
done

# 4. Portability Audit
echo -e "\n${CYAN}→${NC} Running Portability Audit..."
ABS_PATHS=$(grep -r "/Users/" . --exclude-dir=".git" --exclude-dir="venv" --exclude-dir=".gemini" | wc -l)
if [ "$ABS_PATHS" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No absolute paths found. Workspace is portable."
else
    echo -e "${YELLOW}⚠ Found $ABS_PATHS potential absolute paths!${NC}"
    echo "   Run: grep -r \"/Users/\" . --exclude-dir=\".git\" --exclude-dir=\"venv\""
fi

# 5. Done
echo -e "\n${GREEN}✨ DNK HUB Workspace is ready!${NC}"
echo -e "Агент ${YELLOW}DNK_core_ingener${NC} тепер може розпочинати роботу."
