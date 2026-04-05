
ai-agent() {
    # Colors
    local CYAN='\033[0;36m'
    local GREEN='\033[0;32m'
    local RED='\033[0;31m'
    local YELLOW='\033[1;33m'
    local BLUE='\033[0;34m'
    local NC='\033[0m'

    if [ -z "$1" ]; then
        echo -e "${YELLOW}Usage:${NC} ai-agent \"Task Description\"" >&2
        return 1
    fi

    # Create Temp Files & Setup Cleanup
    local tempPersona=$(mktemp)
    local tempRules=$(mktemp)
    local tempCombined=$(mktemp)
    trap 'rm -f "$tempPersona" "$tempRules" "$tempCombined"' RETURN EXIT

    # Header to stderr
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    echo -e "${CYAN}🚀 UNIFIED ARCHITECT AGENT${NC}" >&2
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2

    # Stage 1: Generate Persona
    echo -e "${YELLOW}◈ STAGE 1:${NC} Extracting Domain Expertise..." >&2
    ai-dev -tf "$HOME/Ai/system/prompt-creator.md" --msg "$1" --no-think-anim -o "$tempPersona" > /dev/null
    echo -e "${GREEN}✓ Persona Generated.${NC}" >&2

    # Stage 2: Inject Agentic Logic
    echo -e "${YELLOW}◈ STAGE 2:${NC} Injecting Agentic DNA..." >&2
    ai-dev -tf "$HOME/Ai/system/agent-prompt-creator.md" --msg "$(cat "$tempPersona")" --no-think-anim -o "$tempRules" > /dev/null
    echo -e "${GREEN}✓ DNA Injected.${NC}" >&2

    # Stage 3: Compiling Final System Prompt to File
    cat <<EOF > "$tempCombined"
$(cat "$tempPersona")

# MANDATORY JSON FORMAT
**You are strictly FORBIDDEN from wrapping your response in Markdown code blocks (e.g., \`\`\`json).
** Your entire output must be a single, raw JSON object.
$(cat "$tempRules")
EOF

    echo -e "${GREEN}✓ System Prompt Compiled.${NC}" >&2

    # Stage 4: Execution
    echo -e "${YELLOW}◈ STAGE 3:${NC} Starting Agent Execution..." >&2
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    
    local userQuery="$1"
    shift
    # We use the combined file as the template (-tf) and pass the original task as the message
    ai-dev -tf "$tempCombined" --agent --msg "$userQuery" --pipeline "pipelines/single_agent.json" "$@"
}


ai-agent-build() {
    # Colors
    local CYAN='\033[0;36m'
    local GREEN='\033[0;32m'
    local RED='\033[0;31m'
    local YELLOW='\033[1;33m'
    local BLUE='\033[0;34m'
    local NC='\033[0m'

    if [ -z "$1" ]; then
        echo -e "${YELLOW}Usage:${NC} ai-agent-build \"Task Description\" [output_file.md]" >&2
        return 1
    fi

    local TARGET_FILE="$2"

    # 1. Check for Overwrite
    if [ -n "$TARGET_FILE" ] && [ -f "$TARGET_FILE" ]; then
        echo -en "${RED}⚠️  WARNING:${NC} File '${TARGET_FILE}' exists. Overwrite? (y/n): " >&2
        read -r CONFIRM
        if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Operation cancelled.${NC}" >&2
            return 1
        fi
    fi

    # Create Temp Files & Setup Cleanup
    local tempPersona=$(mktemp)
    local tempRules=$(mktemp)
    trap 'rm -f "$tempPersona" "$tempRules"' RETURN EXIT

    # Header to stderr
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    echo -e "${CYAN}🚀 UNIFIED ARCHITECT COMPILER${NC}" >&2
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2

    # Stage 1: Generate Persona (Output to file)
    echo -e "${YELLOW}◈ STAGE 1:${NC} Extracting Domain Expertise..." >&2
    ai-dev -tf "$HOME/Ai/system/prompt-creator.md" --msg "$1" -o "$tempPersona" > /dev/null
    echo -e "${GREEN}✓ Persona Generated.${NC}" >&2

    # Stage 2: Inject Agentic Logic (Read from tempPersona, Output to tempRules)
    echo -e "${YELLOW}◈ STAGE 2:${NC} Injecting Agentic DNA..." >&2
    ai-dev -tf "$HOME/Ai/system/agent-prompt-creator.md" --msg "$(cat "$tempPersona")"  -o "$tempRules" > /dev/null
    echo -e "${GREEN}✓ DNA Injected.${NC}" >&2

    # Stage 3: Compiling Final Prompt
    local FINAL_PROMPT
    FINAL_PROMPT=$(cat <<EOF
$(cat "$tempPersona")

# MANDATORY JSON FORMAT
**You are strictly FORBIDDEN from wrapping your response in Markdown code blocks (e.g., \`\`\`json).
** Your entire output must be a single, raw JSON object.

$(cat "$tempRules")
EOF
)

    # Output Management
    if [ -n "$TARGET_FILE" ]; then
        mkdir -p "$(dirname "$TARGET_FILE")"
        echo "$FINAL_PROMPT" > "$TARGET_FILE"
        echo -e "${GREEN}✔ SAVED TO:${NC} $TARGET_FILE" >&2
    else
        echo -e "${GREEN}✔ COMPILATION COMPLETE${NC}" >&2
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
        echo "$FINAL_PROMPT"
    fi
}

ai-persona-build() {
    # Colors
    local CYAN='\033[0;36m'
    local GREEN='\033[0;32m'
    local RED='\033[0;31m'
    local YELLOW='\033[1;33m'
    local BLUE='\033[0;34m'
    local NC='\033[0m'

    if [ -z "$1" ]; then
        echo -e "${YELLOW}Usage:${NC} ai-persona-build \"Task Description\" [output_file.md]" >&2
        return 1
    fi

    local TARGET_FILE="$2"

    if [ -n "$TARGET_FILE" ] && [ -f "$TARGET_FILE" ]; then
        echo -en "${RED}⚠️  WARNING:${NC} Persona file '${TARGET_FILE}' exists. Overwrite? (y/n): " >&2
        read -r CONFIRM
        if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Operation cancelled.${NC}" >&2
            return 1
        fi
    fi

    # Create Temp File
    local tempPersona=$(mktemp)
    trap 'rm -f "$tempPersona"' RETURN EXIT

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
    echo -e "${CYAN}🎭 DOMAIN PERSONA COMPILER${NC}" >&2
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2

    echo -e "${YELLOW}◈ EXTRACTING:${NC} Generating Domain Expert Persona..." >&2
    ai-dev --system-file "$HOME/Ai/system/prompt-creator.md" --msg "$1"  -o "$tempPersona" > /dev/null
    
    if [ -n "$TARGET_FILE" ]; then
        mkdir -p "$(dirname "$TARGET_FILE")"
        mv "$tempPersona" "$TARGET_FILE"
        echo -e "${GREEN}✓ SAVED TO:${NC} $TARGET_FILE" >&2
    else
        echo -e "${GREEN}✓ EXTRACTION COMPLETE${NC}" >&2
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" >&2
        cat "$tempPersona"
    fi
}