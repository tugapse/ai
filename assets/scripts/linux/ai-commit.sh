#!/bin/bash
# FIXME missing tool
# TODO incomplete, missing gitdiff tool

# ==============================================================================
# Script: ai-commit.sh
# Description: Self-Contained Agentic Commit Generator
# Features: Diff Sanitization, Clean Output (-o Logic), No-Change Fail-Safe
# Author: Fábio Almeida
# Project: Just A Reasoning Virtual Intelligent Sentinel Agentic Interface
# ==============================================================================

set -e

# --- ANSI COLORS & TEXT FORMATTING ---
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' 

# --- LOCAL UI FUNCTIONS ---
ui_section()  { echo -e "\n${BOLD}${CYAN}● $1${NC}"; ui_divider; }
ui_info()     { echo -e "${CYAN}○${NC} $1"; }
ui_warn()     { echo -e "${YELLOW}⚠${NC} $1"; }
ui_error()    { echo -e "${RED}✖${NC} $1"; }
ui_success()  { echo -e "${GREEN}✔${NC} $1"; }
ui_box()      { echo -e "\n${CYAN}┌── $1 ────────────────────${NC}\n$2\n${CYAN}└──────────────────────────────────────────${NC}"; }
ui_divider()  { echo -e "${CYAN}────────────────────────────────────────────────${NC}"; }
ui_property() { printf "${BOLD}%-15s:${NC} %b\n" "$1" "$2"; }
ui_confirm()  {
    echo -ne "\n${YELLOW}${BOLD}⚡ $1 (y/N): ${NC}"
    read -r response
    [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]
}

# --- GLOBAL CONFIGURATION ---
AI_ENGINE=${AI_ENGINE:-ai}
AI_ENGINE_DEFAULT_MODEL=${AI_ENGINE_DEFAULT_MODEL:-default}

# Runtime state
TEMP_MSG_FILE=$(mktemp)

# --- SIGNAL HANDLING ---
cleanup() {
    rm -f "$TEMP_MSG_FILE"
    echo -e "${NC}"
}
trap cleanup EXIT SIGINT SIGTERM

# --- MAIN EXECUTION ---
main() {
    # 1. Capture Diff (Using your -b logic)
    DIFF_CONTENT=$(gitdiff . -b 2>/dev/null || git diff --staged)

    # 2. Validation: No changes detected
    if [[ -z "$DIFF_CONTENT" ]] || [[ "$DIFF_CONTENT" == *"No changes detected"* ]]; then
        ui_info "No changes detected. Workspace is clean."
        exit 0
    fi

    ui_section "INITIALIZING COMMIT ENGINE"
    ui_property "AI Model" "$AI_ENGINE_DEFAULT_MODEL"
    ui_property "Diff Size" "${BOLD}$(echo "$DIFF_CONTENT" | wc -l) lines${NC}"

    ui_info "Analyzing changes and generating message..."

    # 3. AI Generation (Using -o and --no-out for clean output)
    if ! "$AI_ENGINE" -md "$AI_ENGINE_DEFAULT_MODEL" \
        --system task \
        --task commit \
        --msg "$DIFF_CONTENT" \
        --no-out \
        -o "$TEMP_MSG_FILE" "$@"; then
        
        ui_error "AI Engine failed to generate commit message."
        exit 1
    fi

    # 4. Review & Execution
    if [ -s "$TEMP_MSG_FILE" ]; then
        COMMIT_MSG=$(cat "$TEMP_MSG_FILE")
        ui_box "PROPOSED COMMIT MESSAGE" "$COMMIT_MSG"
        
        if ui_confirm "Proceed with git commit?"; then
            # Clean up the message (strip surrounding quotes if AI added them)
            CLEAN_MSG=$(echo "$COMMIT_MSG" | sed -e 's/^"//' -e 's/"$//')
            
            if git commit -m "$CLEAN_MSG"; then
                ui_success "Changes committed successfully!"
            else
                ui_error "Git commit failed."
                exit 1
            fi
        else
            ui_warn "Commit cancelled."
        fi
    else
        ui_error "Generated message was empty. Check your 'commit' task prompt."
        exit 1
    fi
}

main "$@"