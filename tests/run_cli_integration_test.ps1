$ErrorActionPreference = "Stop"

# CLI Integration Test Skeleton

$env:AI_ASSISTANT_DIRECTORY = if ([System.Environment]::OSVersion.Platform -eq 'Win32NT') { "$env:TEMP\ai_assistant_test_dir" } else { "/tmp/ai_assistant_test_dir" }

$TEST_MODEL_CONFIG = New-TemporaryFile | Rename-Item -NewName { $_.Name + ".json" } -PassThru

@"
{
  "model_name": "gemma4",
  "model_type": "gguf",
  "model_properties": {
    "gguf_filename": "gemma-4-E2B-it-Q4_K_M.gguf",
    "model_repo_id": "unsloth/gemma-4-E2B-it-GGUF",
    "n_gpu_layers": -1,
    "n_ctx": 2048,
    "verbose": false,
    "max_new_tokens": 512,
    "temperature": 0.1,
    "top_p": 0.5,
    "top_k": 50,
    "presence_penalty": 1,
    "frequency_penalty": 1
  }
}
"@ | Set-Content -Path $TEST_MODEL_CONFIG.FullName

$env:MODEL_TO_USE = $TEST_MODEL_CONFIG.FullName
$env:AI_CMD = "pwsh -File ./run.ps1 -dc -md `"$env:MODEL_TO_USE`""

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$SCRIPT_DIR/e2e/test_utils.ps1"
. "$SCRIPT_DIR/e2e/test_category_1_info.ps1"
. "$SCRIPT_DIR/e2e/test_category_2_single_turn.ps1"
. "$SCRIPT_DIR/e2e/test_category_3_fs_modifiers.ps1"
. "$SCRIPT_DIR/e2e/test_category_4_config_state.ps1"
. "$SCRIPT_DIR/e2e/test_category_5_blocking.ps1"

try {
    run_category_1
    run_category_2
    run_category_3
    run_category_4
    run_category_5
    print_summary
} finally {
    Remove-Item -Force $TEST_MODEL_CONFIG.FullName -ErrorAction SilentlyContinue
}

# ==============================================================================
# TODO: Pending Implementations
# ==============================================================================
# Test: --image
# Test: --pipeline
# Test: --create-tool
# Test: --generate-config

# TODO: Implement remaining tests: -D, -e, -q, -pl, -pdb, -nta
# Test: Interactive mode
# Test: --install
# Test: --overwrite-config
