# Autocomplete function for the 'ai.ps1' script
# Add this to your PowerShell profile (type 'notepad $PROFILE' in PowerShell to open/create it).

Register-ArgumentCompleter -CommandName 'ai.ps1' -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)

    $completionResults = @()

    # Define the AI_ASSISTANT_DIRECTORY, similar to the Bash script.
    # It checks if an environment variable `AI_ASSISTANT_DIRECTORY` is set,
    # otherwise defaults to '$Home\Ai' (which is typically 'C:\Users\<YourUsername>\Ai').
    $aiAssistantDirectory = If ($env:AI_ASSISTANT_DIRECTORY) {
        $env:AI_ASSISTANT_DIRECTORY
    } Else {
        "$Home\Ai"
    }

    # --- Bash "Block Part": Flag and Option Completion ---
    # This section suggests parameter names (e.g., --msg, -m).
    # We explicitly list all possible parameters and their aliases.
    $allKnownParameters = @(
        '--msg', '-m',
        '--model', '-md',
        '--system', '-s',
        '--system-file', '-sf',
        '--list-models', '-l',
        '--file', '-f',
        '--image', '-i',
        '--load-folder', '-D',
        '--ext', '-e',
        '--task', '-t',
        '--task-file', '-tf',
        '--output-file', '-o',
        '--auto-task', '-at',
        '--print-chat', '-p',
        '--no-think-anim',
        '--print-log', '-pl',
        '--print-debug', '-pdb',
        '--no-out', '-q',
        '--debug-console', '-dc',
        '--generate-config',
        '--model-type'
    )

    # If the user is currently typing a word that starts with a dash, suggest parameters.
    # This part handles initial parameter name completion (e.g., typing `-m` and hitting Tab).
    if ($wordToComplete.StartsWith('-')) {
        $completionResults += $allKnownParameters | Where-Object { $_ -like "$wordToComplete*" }
    }

    # --- Bash "Block Part": Handle specific argument completions (e.g., filenames) ---
    # This section provides completions for the *values* of specific parameters.
    # It checks the last parameter entered by the user to provide context-aware suggestions.

    # Find the last parameter that was typed in the command line using CommandParameterAst.
    # We use `-ErrorAction SilentlyContinue` to avoid errors if there's no previous parameter.
    $prevParameterAst = $commandAst.FindAll({ $args[0] -is [System.Management.Automation.Language.CommandParameterAst] }, $true) | Select-Object -Last 1 -ErrorAction SilentlyContinue
    $prevParameterName = $prevParameterAst.ParameterName

    # Use a switch statement to provide different completions based on the previous parameter.
    switch ($prevParameterName) {
        # Handles `--model-type` with fixed options
        "model-type" {
            $options = @("causal_lm", "ollama", "gguf")
            $completionResults += $options | Where-Object { $_ -like "$wordToComplete*" }
        }

        # Handles `--task` and `-t` by listing markdown files in the 'task' directory
        "task" {
            $taskDir = Join-Path $aiAssistantDirectory "task"
            if (Test-Path $taskDir) {
                $completionResults += (Get-ChildItem -Path $taskDir -Filter "*.md" -File -Name "$wordToComplete*.md" |
                                       ForEach-Object { $_.BaseName })
            }
        }
        "t" {
            $taskDir = Join-Path $aiAssistantDirectory "task"
            if (Test-Path $taskDir) {
                $completionResults += (Get-ChildItem -Path $taskDir -Filter "*.md" -File -Name "$wordToComplete*.md" |
                                       ForEach-Object { $_.BaseName })
            }
        }

        # Handles `--model` and `-md` by listing JSON files in the 'model-config' directory
        "model" {
            $modelConfigDir = Join-Path $aiAssistantDirectory "model-config"
            if (Test-Path $modelConfigDir) {
                $completionResults += (Get-ChildItem -Path $modelConfigDir -Filter "*.json" -File -Name "$wordToComplete*.json" |
                                       ForEach-Object { $_.BaseName })
            }
        }
        "md" {
            $modelConfigDir = Join-Path $aiAssistantDirectory "model-config"
            if (Test-Path $modelConfigDir) {
                $completionResults += (Get-ChildItem -Path $modelConfigDir -Filter "*.json" -File -Name "$wordToComplete*.json" |
                                       ForEach-Object { $_.BaseName })
            }
        }

        # Handles `--system` and `-s` by listing markdown files in the 'system' directory
        "system" {
            $systemDir = Join-Path $aiAssistantDirectory "system"
            if (Test-Path $systemDir) {
                $completionResults += (Get-ChildItem -Path $systemDir -Filter "*.md" -File -Name "$wordToComplete*.md" |
                                       ForEach-Object { $_.BaseName })
            }
        }
        "s" {
            $systemDir = Join-Path $aiAssistantDirectory "system"
            if (Test-Path $systemDir) {
                $completionResults += (Get-ChildItem -Path $systemDir -Filter "*.md" -File -Name "$wordToComplete*.md" |
                                       ForEach-Object { $_.BaseName })
            }
        }

        # Handle file/image/system-file/load-folder/auto-task/output-file/print-chat completions
        # These correspond to Bash's `_filedir`.
        "file", "f", "image", "i", "system-file", "sf", "task-file", "tf", "output-file", "o", "print-chat", "p", "auto-task", "at" {
            # Provide file completion, including partial matches
            $completionResults += Get-ChildItem -Path "$wordToComplete*" -File | Select-Object -ExpandProperty Name
        }

        # Handle load-folder completion (directories only)
        # This corresponds to Bash's `_filedir -d`.
        "load-folder", "D", "generate-config" {
            # Provide directory completion, including partial matches
            $completionResults += Get-ChildItem -Path "$wordToComplete*" -Directory | Select-Object -ExpandProperty Name
        }

        default {
            # Default to file/directory completion if no specific parameter match and the current word
            # is not starting with a dash (meaning it's likely a positional argument or a general file path).
            if (-not $wordToComplete.StartsWith('-')) {
                $completionResults += Get-ChildItem -Path "$wordToComplete*" | Select-Object -ExpandProperty Name
            }
        }
    }

    # Format the results into CompletionResult objects, which PowerShell expects.
    # This also adds a ToolTip, which is helpful for users.
    $completionResults | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
