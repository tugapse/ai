# CLI Arguments Testing Plan

## Overview
This plan outlines the strategy for integration testing the CLI interface. We will test the system entry point with various arguments to ensure stable behavior, correct output, and proper exit codes. 

*Note: The test script will execute the CLI via the `run.sh` wrapper script to replicate the actual user execution environment.*

## Argument Categories & Execution Strategy

### 1. Informational & Immediate Exit (Non-Blocking)
These arguments should print information and exit cleanly with a zero exit code.
- `-h`, `--help`: Validate that the help message ("usage: ai [OPTIONS]") is printed.
- `-v`, `--version`: Validate that the version string is outputted.
- `-l`, `--list-models`: Validate that the list of available models is printed. *(Note: This is currently expected to fail. We will implement the feature alongside the test.)*
- `--show-logo` (with `-v`): Validate that the JARVIS ASCII logo is printed. Must be appended with `--version` or `-v` to prevent triggering the interactive program loop.

**Test Approach:** Execute and assert exit code `0` and grep for expected text in `stdout`.

### 2. Single-Turn Execution (Expected Auto-Exit)
These commands execute a specific task or query and should exit after completion. We must ensure they don't fall back into an interactive read loop.
- `-m`, `--msg`: Pass a simple query (`-m "Hello"`) and ensure it completes and exits.
- `-f`, `--file`: Pass a dummy text file along with a prompt (`-m "what text or number is on the file"`) to trigger the LLM and verify the content matches the file.
- `-tf`, `--task-file`: Create a temporary file with the content "1+1", run it with this flag, and verify the LLM outputs "2".

**Test Approach:** Provide simple static inputs, run the command, assert that execution concludes within a reasonable time, and verify a zero exit code.

### 3. File System Modifiers
These commands modify or create files on disk. 
- `--create-tool TOOL_NAME`: Should generate a tool template file.
- `--generate-config FILENAME` + `--model-type TYPE`: Should generate a config manifest.
- `-o`, `--output-file OUTPUT_FILE`: Run a simple query (e.g., `-m "Hello" -o temp_out.txt`) and verify that `temp_out.txt` is created and contains the response content.

**Test Approach:** 
1. Run the command specifying a temporary output path.
2. Verify the exit code.
3. Assert that the file exists and contains the expected initial boilerplate/content.
4. Clean up generated files after the test.

### 4. Configuration & State Overrides
These flags modify how the application runs but don't inherently change the execution shape. They should be combined with a single-turn execution (like `-m "test"`) to be tested properly.
- `-md`, `--model`: Run 2 tests with different models, asking for the model's name (e.g., `-m "What is your model name?"`). Deterministic parameters will be provided later to ensure consistent output.
- `-sf`, `--system-file`: Inject a system prompt file.

**Test Approach:** Run in conjunction with `-m "test"`, verifying the specific configuration effects.

### 5. Blocking / Long-Running Processes
These arguments intentionally block the process (e.g., starting a server or an interactive chat).
- `--server`: Starts the Brain Server module.
- (No arguments / interactive mode): Starts a standard interactive session.

**Test Approach:** 
- Use process timeouts (e.g., `timeout 300s ...`) to run the command.
- For the server: Start the process in the background. Wait a couple of seconds to allow it to initialize, perform a GET request to the health endpoint to verify it is running, and then gracefully terminate the server process using `kill`.
- For interactive mode: Pipe a simple command to `stdin` or use `expect` scripts to simulate a user session, then send an exit command or EOF.



## Implementation Details

We will create a shell script (e.g., `tests/integration/cli_integration_test.sh` or integrate into `test.sh`) structured around a test runner function.

**Helper Function Example:**
```bash
function test_cli() {
    local test_name=$1
    local args=$2
    local expected_exit_code=${3:-0}
    local timeout_duration=${4:-10s}
    
    echo "Running Test: $test_name"
    # execute via timeout to prevent hangs
    output=$(timeout $timeout_duration ./run.sh $args 2>&1)
    exit_code=$?
    
    if [ $exit_code -ne $expected_exit_code ]; then
        echo "❌ FAILED: Expected exit code $expected_exit_code but got $exit_code"
        return 1
    fi
    echo "✅ PASSED: $test_name"
    return 0
}
```

## TODO (Future Tests)
The following tests and argument verifications are deferred for future implementation:
- `-D`, `--load-folder` & `-e`, `--ext`: Point to a dummy directory and test vector memory loading.
- `--session-id`: Set a specific session ID and check if memory is managed.
- `-q`, `--no-out`: Ensure stdout has minimal/no output.
- `-pl`, `--print-log` / `-pdb`, `--print-debug`: Check if telemetry/verbose streams are present in stdout/stderr.
- `-nta`, `--no-think-anim`: Ensure no terminal control characters associated with animations are outputted.
- `--image`: Pass a test image file and verify the response.
- `--pipeline`: Test against a known pipeline JSON.
- `--create-tool`: Generate a tool template file.
- `--generate-config`: Generate a config manifest.
- `--install`: Sync dependencies.
- `--overwrite-config`: Verify existing configuration logic override.
- `--install`: Syncs dependencies. 
- `--overwrite-config`: Overrides existing configuration logic.


## Next Steps
1. Review this plan to ensure all edge cases and argument combinations of interest are covered.
2. Begin writing `tests/integration/cli_integration_test.sh` to implement the test cases defined above.
