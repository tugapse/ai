# Exit immediately if a command exits with a non-zero status.
$ErrorActionPreference = 'Stop'

# Define test script paths
$CLI_INTEGRATION_TEST_SCRIPT = "tests/run_cli_integration_test.sh"
$UNIT_TEST_SCRIPT = "tests/run_tests.sh"

# Initialize flags
$RUN_UNIT_TESTS_FLAG = $false
$RUN_CLI_INTEGRATION_TESTS_FLAG = $false
$ANY_SPECIFIC_FLAG_SET = $false
$env:VERBOSE = "0"

# Function to display help message
function Show-Help {
    $scriptName = Split-Path -Leaf $MyInvocation.MyCommand.Path
    Write-Host "Usage: .\$scriptName [OPTIONS]"
    Write-Host "Run various test suites for the project."
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -u, --unit               Run only unit tests."
    Write-Host "  -c, --cli                Run only CLI integration tests."
    Write-Host "  -a, --all                Run all tests (default behavior if no specific test is chosen)."
    Write-Host "  -v, --verbose            Display LLM output during tests."
    Write-Host "  -h, --help               Display this help message and exit."
    Write-Host ""
}

# Parse command-line arguments
foreach ($arg in $args) {
    switch ($arg) {
        { $_ -match "^(-v|--verbose)$" } {
            $env:VERBOSE = "1"
        }
        { $_ -match "^(-u|--unit)$" } {
            $RUN_UNIT_TESTS_FLAG = $true
            $ANY_SPECIFIC_FLAG_SET = $true
        }
        { $_ -match "^(-c|--cli)$" } {
            $RUN_CLI_INTEGRATION_TESTS_FLAG = $true
            $ANY_SPECIFIC_FLAG_SET = $true
        }
        { $_ -match "^(-a|--all)$" } {
            $RUN_UNIT_TESTS_FLAG = $true
            $RUN_CLI_INTEGRATION_TESTS_FLAG = $true
            $ANY_SPECIFIC_FLAG_SET = $true
        }
        { $_ -match "^(-h|--help)$" } {
            Show-Help
            exit 0
        }
        default {
            Write-Host "Error: Unknown option: $_"
            Show-Help
            exit 1
        }
    }
}

# If no specific flags were set, run both by default
if (-not $ANY_SPECIFIC_FLAG_SET) {
    Show-Help
    exit 1
}

# Execute selected tests
if ($RUN_UNIT_TESTS_FLAG) {
    Write-Host "========================================"
    Write-Host "Running Unit Tests"
    Write-Host "========================================"
    & bash $UNIT_TEST_SCRIPT
}

if ($RUN_CLI_INTEGRATION_TESTS_FLAG) {
    Write-Host "========================================"
    Write-Host "Running CLI Integration Tests"
    Write-Host "========================================"
    & bash $CLI_INTEGRATION_TEST_SCRIPT
}

if (-not $RUN_UNIT_TESTS_FLAG -and -not $RUN_CLI_INTEGRATION_TESTS_FLAG) {
    Write-Host "No tests selected to run."
    exit 0
}

Write-Host "All selected tests finished."