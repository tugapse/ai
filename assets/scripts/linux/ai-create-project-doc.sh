#!/bin/bash

# ==============================================================================
# Script: ai-create-project-doc.sh
# Description: Self-Contained Modular Documentation Engine (Git-Diff Aware)
# Features: Thermal Throttling, Server Mode, Incremental Documentation (Git)
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
ui_divider()  { echo -e "${CYAN}────────────────────────────────────────────────${NC}"; }
ui_property() { printf "${BOLD}%-15s:${NC} %b\n" "$1" "$2"; }

ui_confirm()  {
    echo -ne "\n${YELLOW}${BOLD}⚡ $1 (y/N): ${NC}"
    read -r response
    [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]
}

# --- GLOBAL CONFIGURATION ---
AI_ENGINE=${AI_ENGINE:-ai}
AI_ENGINE_DEFAULT_MODEL="${AI_ENGINE_DEFAULT_MODEL:-custom/task/create-project-doc}"

# Runtime state
TEMP_LIST=""
TOTAL_FILES=0
MANIFEST=""
ENGINE_START_TIME=0
SILENT_FLAG=""
SERVER_PID=""
USE_SERVER=false
DIFF_MODE=false
DIFF_TARGET="master"

# --- SIGNAL HANDLING ---
cleanup() {
    echo -e "${NC}"
    if [ -n "$SERVER_PID" ]; then
        ui_warn "Shutting down AI Server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    [ -f "$TEMP_LIST" ] && rm -f "$TEMP_LIST"
    ui_warn "Documentation Engine halted."
    exit 130
}
trap cleanup SIGINT SIGTERM

# --- UTILITY FUNCTIONS ---
sanitize_path() {
    realpath -m "$1" 2>/dev/null || echo "$1"
}

show_help() {
    local cmd_name=$(basename "$0")
    ui_section "AI DOCUMENTATION ENGINE HELP"
    echo -e "${BOLD}Usage:${NC} $cmd_name [flags] <ext> <src> <dst> [out_ext]"
    echo -e ""
    echo -e "${BOLD}Positional Arguments:${NC}"
    echo -e "  ${CYAN}ext${NC}              File extension to scan (e.g., py, php, js)"
    echo -e "  ${CYAN}src${NC}              Source directory containing the code"
    echo -e "  ${CYAN}dst${NC}              Destination directory for mirrored docs"
    echo -e "  ${CYAN}out_ext${NC}          Output file extension (default: .md)"
    echo -e ""
    echo -e "${BOLD}Flags:${NC}"
    echo -e "  ${YELLOW}-d,  --diff [br]${NC}   Only document files changed vs master (or [br])"
    echo -e "  ${YELLOW}-S,  --server${NC}      Enable background server mode (Persistence)"
    echo -e "  ${YELLOW}-m,  --model${NC}       Override AI model (Current: $AI_ENGINE_DEFAULT_MODEL)"
    echo -e "  ${YELLOW}-r,  --remote${NC}      Target Remote URL (Default: http://0.0.0.0:9999)"
    echo -e "  ${YELLOW}-t,  --threshold${NC}   Thermal limit in Celsius (Default: 80)"
    echo -e "  ${YELLOW}-s,  --sleep${NC}       Cooldown seconds when throttled (Default: 30)"
    echo -e "  ${YELLOW}-si, --silent${NC}      Pass --no-out to the AI engine"
    echo -e "  ${YELLOW}-h,  --help${NC}        Display this help menu"
    echo -e ""
    echo -e "${BOLD}Thermal Logic:${NC}"
    echo -e "  Monitors 'rs-temp -s' before each file. If any sensor > threshold, it sleeps."
    exit 0
}

check_thermal_throttle() {
    if [[ "$TEMP_THRESHOLD" -gt 40 ]]; then
        local temp_output=$(rs-temp -s)
        local temps=$(echo "$temp_output" | grep -oE '[0-9]+(\.[0-9]+)?')
        for t in $temps; do
            if (( $(echo "$t > $TEMP_THRESHOLD" | bc -l) )); then
                ui_warn "Thermal limit: ${RED}${t}°C${NC} > ${TEMP_THRESHOLD}°C. Pausing for ${SLEEP_TIME}s..."
                sleep "$SLEEP_TIME"
                check_thermal_throttle
                break
            fi
        done
    fi
}

# --- MODULE 1: MANIFEST & QUEUE GENERATOR ---
generate_queue() {
    TEMP_LIST=$(mktemp)
    
    if [ "$DIFF_MODE" = true ]; then
        ui_info "Identifying changes vs ${CYAN}$DIFF_TARGET${NC}..."
        
        if ! git -C "$SRC_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            ui_error "Source directory is not a Git repository. Cannot use --diff."
            exit 1
        fi

        # Identify files changed in current branch since divergence from target
        git -C "$SRC_DIR" diff --name-only "$DIFF_TARGET"... | \
            grep "\.$EXT$" | \
            while read -r line; do
                local full_path=$(realpath -m "$(git -C "$SRC_DIR" rev-parse --show-toplevel)/$line")
                if [[ "$full_path" == "$SRC_DIR"* ]]; then
                    echo "$full_path" >> "$TEMP_LIST"
                fi
            done || true
    else
        ui_info "Performing full scan for ${CYAN}*.$EXT${NC} files..."
        find "$SRC_DIR" -type f -name "*.$EXT" > "$TEMP_LIST"
    fi

    TOTAL_FILES=$(wc -l < "$TEMP_LIST")
    [ "$TOTAL_FILES" -eq 0 ] && ui_error "No files found to process." && exit 1
    
    local doc_root=$(basename "$DST_DIR")
    MANIFEST=$(sed "s|^$SRC_DIR/|/$doc_root/|; s|\.$EXT$|.$CLEAN_OUT|" "$TEMP_LIST" | paste -sd ',' -)
}

# --- MODULE 2: SERVER ORCHESTRATOR ---
start_ai_server() {
    ui_info "Launching background AI Server with model: ${CYAN}$AI_ENGINE_DEFAULT_MODEL${NC}..."
    $AI_ENGINE --server -md "$AI_ENGINE_DEFAULT_MODEL" > /dev/null 2>&1 &
    SERVER_PID=$!
    
    ui_info "Waiting for server to bind to $REMOTE_TARGET..."
    until curl -s "$REMOTE_TARGET" > /dev/null 2>&1; do
        sleep 2
        echo -n "."
    done
    echo -e " ${GREEN}Ready!${NC}"
}

# --- MODULE 3: SINGLE FILE PROCESSOR ---
process_single_file() {
    local file="$1"
    local current_step="$2"
    local turn_start=$(date +%s.%N)
    local rel_path="${file#$SRC_DIR/}"
    local target_file="$DST_DIR/${rel_path%.$EXT}.$CLEAN_OUT"
    
    mkdir -p "$(dirname "$target_file")"

    local eta_str="${YELLOW}Calculating...${NC}"
    if [ "$current_step" -gt 1 ]; then
        local now=$(date +%s.%N)
        local elapsed=$(echo "$now - $ENGINE_START_TIME" | bc)
        local completed=$((current_step - 1))
        local avg_sec=$(echo "scale=4; $elapsed / $completed" | bc)
        local remaining=$((TOTAL_FILES - completed))
        local eta_min=$(echo "scale=2; (($TOTAL_FILES - $completed) * $avg_sec) / 60" | bc)
        eta_str="${GREEN}${eta_min}m${NC}"
    fi

    ui_info "[${BOLD}${CYAN}$current_step/$TOTAL_FILES${NC}] Processing: ${BOLD}$rel_path${NC} (ETA: $eta_str)"

    local task="create-code-documentation"

    local ai_args=(-md "$AI_ENGINE_DEFAULT_MODEL" -o "$target_file" --task "$task" --system task --file "$file" --msg "MANIFEST: $MANIFEST")
    [[ -n "$SILENT_FLAG" ]] && ai_args+=("$SILENT_FLAG")
    [[ "$USE_SERVER" == true ]] && ai_args+=(--remote "$REMOTE_TARGET")

    if ! $AI_ENGINE "${ai_args[@]}" < /dev/null 2>/dev/null; then
        ui_error "Failed to document: $rel_path"
        exit 1
    fi

    local turn_end=$(date +%s.%N)
    local turn_duration_min=$(echo "scale=2; ($turn_end - $turn_start) / 60" | bc)

    ui_success "Generated: ${GREEN}${rel_path%.$EXT}.$CLEAN_OUT${NC} (${turn_duration_min}m)"
    ui_divider
}

# --- MAIN EXECUTION ---
main() {
    TEMP_THRESHOLD=80
    SLEEP_TIME=30
    SILENT_FLAG=""
    REMOTE_TARGET="http://0.0.0.0:9999"
    USE_SERVER=false
    pos_args=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -d|--diff)
                DIFF_MODE=true
                if [[ -n "$2" && "$2" != -* ]]; then
                    DIFF_TARGET="$2"; shift 2
                else
                    shift
                fi
                ;;
            -S|--server)    USE_SERVER=true; shift ;;
            -m|--model)     AI_ENGINE_DEFAULT_MODEL="$2"; shift 2 ;;
            -r|--remote)    REMOTE_TARGET="$2"; shift 2 ;;
            -t|--threshold) TEMP_THRESHOLD="$2"; shift 2 ;;
            -s|--sleep)     SLEEP_TIME="$2"; shift 2 ;;
            -si|--silent)   SILENT_FLAG="--no-out"; shift ;;
            -h|--help)      show_help ;;
            *)              pos_args+=("$1"); shift ;;
        esac
    done

    [ ${#pos_args[@]} -lt 3 ] && show_help

    EXT="${pos_args[0]}"
    SRC_DIR=$(realpath "${pos_args[1]}")
    DST_DIR=$(sanitize_path "${pos_args[2]}")
    OUT_EXT="${pos_args[3]:-.md}"
    CLEAN_OUT="${OUT_EXT#.}"

    generate_queue
    
    ui_section "INITIALIZING DOCUMENTATION ENGINE"
    ui_property "Scan Mode" "$([ "$DIFF_MODE" == true ] && echo -e "${CYAN}Git Diff ($DIFF_TARGET)${NC}" || echo -e "Full Directory")"
    ui_property "Execution" "$([ "$USE_SERVER" == true ] && echo -e "${CYAN}Persistent Server${NC}" || echo -e "Standard Local")"
    ui_property "AI Model" "$AI_ENGINE_DEFAULT_MODEL"
    ui_property "Source" "$SRC_DIR"
    ui_property "Destination" "$DST_DIR"
    ui_property "Manifest Root" "/$(basename "$DST_DIR")/"
    [[ "$USE_SERVER" == true ]] && ui_property "Remote" "$REMOTE_TARGET"
    ui_property "Thermal Lim" "${YELLOW}${TEMP_THRESHOLD}°C${NC}"
    ui_property "Queue" "${BOLD}$TOTAL_FILES files${NC}"
    
    if ! ui_confirm "Begin documentation workflow?"; then
        exit 0
    fi

    [[ "$USE_SERVER" == true ]] && start_ai_server
    
    ENGINE_START_TIME=$(date +%s.%N)
    local current=0
    while IFS= read -r file; do
        check_thermal_throttle
        (( ++current ))
        process_single_file "$file" "$current"
    done < "$TEMP_LIST"

    local total_dur=$(echo "scale=2; ($(date +%s.%N) - $ENGINE_START_TIME) / 60" | bc)
    ui_section "DOCUMENTATION COMPLETE"
    ui_property "Total Time" "${GREEN}${total_dur}m${NC}"
    
    cleanup 
}

main "$@"