#!/bin/bash
# Shared print functions for consistent formatting across installation scripts

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Symbols
CHECK="${GREEN}✓${NC}"
BULLET="${CYAN}•${NC}"
WARN="${YELLOW}⚠${NC}"
ARROW="${BLUE}→${NC}"

# Package name color (subtle teal/blue)
PKG_COLOR='\033[0;36m'  # Cyan/teal

# Print functions (using printf for better compatibility)
print_header() {
    printf "\n"
    printf "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "${BOLD}${BLUE}  %s${NC}\n" "$1"
    printf "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_section() {
    printf "\n"
    printf "${CYAN}┌─${NC} ${BOLD}${CYAN}%s${NC}\n" "$1"
}

print_success() {
    local msg="$1"
    local pkg="${msg%% *}"
    local rest="${msg#* }"
    if [[ "$pkg" != "$msg" ]]; then
        printf "  ${CHECK} ${GREEN}${PKG_COLOR}%s${NC}${GREEN} %s${NC}\n" "$pkg" "$rest"
    else
        printf "  ${CHECK} ${GREEN}%s${NC}\n" "$msg"
    fi
}

print_info() {
    local msg="$1"
    local pkg="${msg%% *}"
    local rest="${msg#* }"
    if [[ "$pkg" != "$msg" ]]; then
        printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${CYAN}%s${NC}\n" "$pkg" "$rest"
    else
        printf "  ${BULLET} ${CYAN}%s${NC}\n" "$msg"
    fi
}

print_warn() {
    printf "  ${WARN} ${YELLOW}%s${NC}\n" "$1"
}

print_action() {
    local msg="$1"
    local pkg="${msg%% *}"
    local rest="${msg#* }"
    if [[ "$pkg" != "$msg" ]]; then
        printf "  ${ARROW} ${BOLD}${PKG_COLOR}%s${NC}${BOLD} %s${NC}\n" "$pkg" "$rest"
    else
        printf "  ${ARROW} ${BOLD}%s${NC}\n" "$msg"
    fi
}

print_completion() {
    local msg="$1"
    printf "\n"
    printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "${CHECK} ${BOLD}${GREEN}%s${NC}\n" "$msg"
    printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "\n"
}
