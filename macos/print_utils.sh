#!/bin/bash
# Shared print functions for consistent formatting across all scripts.
# Used by: install.sh, brew.sh, scaffold.sh, claude/setup.sh, bin/dotfiles

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# Symbols
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
BULLET="${CYAN}•${NC}"
WARN="${YELLOW}⚠${NC}"
ARROW="${BLUE}→${NC}"
SKIP="${YELLOW}○${NC}"
UPDATE="${YELLOW}↻${NC}"

# Package name color
PKG_COLOR='\033[0;36m'

# --- Headers & Sections ---

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

print_completion() {
    printf "\n"
    printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "${CHECK} ${BOLD}${GREEN}%s${NC}\n" "$1"
    printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    printf "\n"
}

# --- Status messages ---

print_success() {
    printf "  ${CHECK} ${GREEN}%s${NC}\n" "$1"
}

print_info() {
    printf "  ${BULLET} ${CYAN}%s${NC}\n" "$1"
}

print_dim() {
    printf "  ${DIM}%s${NC}\n" "$1"
}

print_warn() {
    printf "  ${WARN} ${YELLOW}%s${NC}\n" "$1"
}

print_warning() { print_warn "$@"; }

print_error() {
    printf "  ${CROSS} ${RED}%s${NC}\n" "$1"
}

# --- Action messages ---

print_action() {
    printf "  ${ARROW} ${BOLD}%s${NC}\n" "$1"
}

print_step() {
    printf "  ${CHECK} %s\n" "$1"
}

print_skip() {
    printf "  ${SKIP} %s ${DIM}(already exists)${NC}\n" "$1"
}

print_update() {
    printf "  ${UPDATE} %s ${DIM}(updated)${NC}\n" "$1"
}

# --- Checklist items ---

print_todo() {
    printf "  ${YELLOW}[ ]${NC} %s\n" "$1"
}

print_todo_optional() {
    printf "  ${CYAN}[-]${NC} ${DIM}%s${NC}\n" "$1"
}

# --- Package install messages (for brew.sh) ---

print_pkg_installed() {
    printf "  ${BULLET} ${PKG_COLOR}%s${NC} ${DIM}already installed${NC}\n" "$1"
}

print_pkg_installing() {
    printf "  ${ARROW} ${BOLD}Installing ${PKG_COLOR}%s${NC}${BOLD}...${NC}\n" "$1"
}

print_pkg_done() {
    printf "  ${CHECK} ${PKG_COLOR}%s${NC} ${GREEN}installed${NC}\n" "$1"
}

print_pkg_fail() {
    printf "  ${WARN} ${YELLOW}Failed to install %s${NC}\n" "$1"
}
