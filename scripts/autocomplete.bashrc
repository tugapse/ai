# Bash Autocompletion for the 'ai' command
# This script handles all flags and arguments defined in the argparse setup.

_ai_completion() {
    AI_ASSISTANT_DIRECTORY="${AI_ASSISTANT_DIRECTORY:-~/Ai}"

    local cur prev words cword
    _init_completion || return

    COMPREPLY=()
    local flags_and_options=""

    # 1. Cognitive Protocols
    flags_and_options+="--help -h "
    flags_and_options+="--version -v "
    flags_and_options+="--msg -m "
    flags_and_options+="--model -md "
    flags_and_options+="--system -s "
    flags_and_options+="--system-file -sf "
    flags_and_options+="--list-models -l "

    # 2. Asset & Context Management
    flags_and_options+="--file -f "
    flags_and_options+="--image -i "
    flags_and_options+="--load-folder -D "
    flags_and_options+="--ext -e "

    # 3. Autonomous Operations
    flags_and_options+="--agent "
    flags_and_options+="--task -t "
    flags_and_options+="--task-file -tf "
    flags_and_options+="--pipeline -ppl "
    flags_and_options+="--session-id "
    flags_and_options+="--output-file -o "

    # 4. Distributed Architecture
    flags_and_options+="--server "
    flags_and_options+="--remote -r "
    flags_and_options+="--modules "

    # 5. System Debug & Maintenance
    flags_and_options+="--print-chat -p "
    flags_and_options+="--print-log -pl "
    flags_and_options+="--print-debug -pdb "
    flags_and_options+="--no-out -q "
    flags_and_options+="--no-think-anim -nta "
    flags_and_options+="--debug-console -dc "
    flags_and_options+="--install "
    flags_and_options+="--overwrite-config "
    flags_and_options+="--create-tool "

    # 6. Model Generation
    flags_and_options+="--generate-config "
    flags_and_options+="--model-type "


    # Check if the current word starts with a dash to suggest flags
    if [[ "${cur}" == -* ]]; then
        COMPREPLY=( $(compgen -W "${flags_and_options}" -- "${cur}") )
        return
    fi
    
    # Handle specific argument completions
    case "${prev}" in
        --model-type)
            # As per main.py, choices are from ModelType enum. Assuming these are the values.
            options="causal_lm ollama gguf gemini openai"
            COMPREPLY=( $(compgen -W "${options}" -- "${cur}") )
            return
            ;;
        --task|-t)
            options="$(ls "$AI_ASSISTANT_DIRECTORY/task" 2>/dev/null | grep .md | sed 's/\\.md//' | tr "\\n"  " " )"
            COMPREPLY=( $(compgen -W "${options}" -- "${cur}") )
            return
            ;;
        --model|-md)
            options="$(ls "$AI_ASSISTANT_DIRECTORY/model-config" 2>/dev/null | grep .json | sed 's/\\.json//' | tr "\\n"  " " )"
            COMPREPLY=( $(compgen -W "${options}" -- "${cur}") )
            return
            ;;
        --pipeline)
            options="$(ls "$AI_ASSISTANT_DIRECTORY/pipelines" 2>/dev/null | grep .json | sed 's/\\.json//' | tr "\\n"  " " )"
            COMPREPLY=( $(compgen -W "${options}" -- "${cur}") )
            return
            ;;
        --system|-s)
            options="$(ls "$AI_ASSISTANT_DIRECTORY/system" 2>/dev/null | grep .md | sed 's/\\.md//' | tr "\\n"  " " )"
            COMPREPLY=( $(compgen -W "${options}" -- "${cur}") )
            return
            ;;
        --file|-f|--image|-i|--system-file|-sf|--load-folder|-D|--task-file|-tf|--pipeline|-ppl|--output-file|-o|--print-chat|-p|--generate-config)
            _filedir
            return
            ;;
        --create-tool)
            # No completion for tool name
            return
            ;;
    esac

    # Default to filename completion for other cases
    _filedir
}

# Register the completion function for the 'ai' command
complete -F _ai_completion ai