# Bash Autocompletion for the 'ai' command
# This script handles all flags and arguments defined in the argparse setup.

_ai_completion() {
    local cur prev words cword
    _init_completion || return

    COMPREPLY=()
    local flags_and_options=""

    # List all main flags and options
    flags_and_options+="--msg -m "
    flags_and_options+="--model -md "
    flags_and_options+="--system -s "
    flags_and_options+="--system-file -sf "
    flags_and_options+="--list-models -l "
    flags_and_options+="--file -f "
    flags_and_options+="--image -i "
    flags_and_options+="--load-folder -D "
    flags_and_options+="--ext -e "
    flags_and_options+="--task -t "
    flags_and_options+="--task-file -tf "
    flags_and_options+="--output-file -o "
    flags_and_options+="--auto-task -at "
    flags_and_options+="--print-chat -p "
    flags_and_options+="--no-think-anim "
    flags_and_options+="--print-log -pl "
    flags_and_options+="--print-debug -pdb "
    flags_and_options+="--no-out -q "
    flags_and_options+="--debug-console -dc "
    flags_and_options+="--generate-config "
    flags_and_options+="--model-type "

    # Check if the current word starts with a dash to suggest flags
    if [[ "${cur}" == -* ]]; then
        COMPREPLY=( $(compgen -W "${flags_and_options}" -- "${cur}") )
        return
    fi
    
    # Handle specific argument completions (e.g., filenames)
    case "${prev}" in
        --file|-f|--image|-i|--system-file|-sf|--load-folder|-D|--auto-task|-at|--output-file|-o|--print-chat|-p)
            _filedir
            return
            ;;
        --generate-config)
            _filedir -d
            return
            ;;
    esac

    # Default to filename completion for other cases
    _filedir
}

# Register the completion function for the 'ai' command
complete -F _ai_completion ai