# Exit immediately if a command exits with a non-zero status.
set -e

# Define test script paths
CLI_INTEGRATION_TEST_SCRIPT="tests/run_cli_integration_test.sh"
UNIT_TEST_SCRIPT="tests/run-unit-test.sh"

# Initialize flags
RUN_UNIT_TESTS_FLAG=0
RUN_CLI_INTEGRATION_TESTS_FLAG=0
ANY_SPECIFIC_FLAG_SET=0
VERBOSE=0


# Function to display help message
show_help() {
  echo "Usage: $(basename "$0") [OPTIONS]"
  echo "Run various test suites for the project."
  echo ""
  echo "Options:"
  echo "  -u, --unit               Run only unit tests."
  echo "  -c, --cli                Run only CLI integration tests."
  echo "  -a, --all                Run all tests."
  echo "  -v, --verbose            Display LLM output during tests."
  echo "  -h, --help               Display this help message and exit."
  echo ""
}


# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -v|--verbose)
      export VERBOSE=1
      ;;
    -u|--unit)
      RUN_UNIT_TESTS_FLAG=1
      ANY_SPECIFIC_FLAG_SET=1
      ;;
    -c|--cli)
      RUN_CLI_INTEGRATION_TESTS_FLAG=1
      ANY_SPECIFIC_FLAG_SET=1
      ;;
    -a|--all)
      RUN_UNIT_TESTS_FLAG=1
      RUN_CLI_INTEGRATION_TESTS_FLAG=1
      ANY_SPECIFIC_FLAG_SET=1
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Error: Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
  shift
done


# If no specific flags were set, run both by default
if [ "$ANY_SPECIFIC_FLAG_SET" -eq 0 ]; then
  show_help
  exit 1
fi

# Execute selected tests
if [ "$RUN_UNIT_TESTS_FLAG" -eq 1 ]; then
  echo "========================================"
  echo "Running Unit Tests"
  echo "========================================"
  "$UNIT_TEST_SCRIPT"
fi

if [ "$RUN_CLI_INTEGRATION_TESTS_FLAG" -eq 1 ]; then
  echo "========================================"
  echo "Running CLI Integration Tests"
  echo "========================================"
  "$CLI_INTEGRATION_TEST_SCRIPT"
fi

if [ "$RUN_UNIT_TESTS_FLAG" -eq 0 ] && [ "$RUN_CLI_INTEGRATION_TESTS_FLAG" -eq 0 ]; then
  echo "No tests selected to run."
  exit 0
fi

echo "All selected tests finished."