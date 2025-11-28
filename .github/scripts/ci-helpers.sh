#!/usr/bin/env bash
# .github/scripts/ci-helpers.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

install_deps_ubuntu() {
    sudo apt update 
    log_info "Installing build-essential for C extensions (like cffi)..."
    sudo apt install -y build-essential
    log_info "Installing libffi-dev for jupyter..."
    sudo apt install -y libffi-dev
    log_info "Installing libjpeg-dev zlib1g-dev for matplotlib(pillow)..."
    sudo apt install -y libjpeg-dev zlib1g-dev
    log_info "Installing gfortran libopenblas-dev for scipy..."
    sudo apt install -y gfortran libopenblas-dev
}

install_deps_darwin() {
    # Homebrew is already installed on GitHub Actions macOS runners
    log_info "Installing dependencies via Homebrew for macOS..."
    # brew install gcc  # Provides gfortran # Already installed in gh CI
    brew install openblas
}

install_deps_windows() {
    log_warn "No system dependency setup for Windows Python 3.14."
    log_warn "If no wheels are available, the build is expected to fail (due to missing MSVC/Fortran compiler)."
}

# Install system dependencies
install_system_deps() {
    local python_version=$1
    local runner_os=$2
    
    if [[ "$python_version" =~ ^3\.(13|14) ]]; then
        log_info "Installing ${runner_os} dependencies for Python ${python_version}..."
        if [[ "$runner_os" == "Linux" ]]; then
            install_deps_ubuntu
        elif [[ "$runner_os" == "macOS" ]]; then
            install_deps_darwin
        elif [[ "$runner_os" == "Windows" ]]; then
            install_deps_windows
        fi
    else
        log_info "Python ${python_version} on ${runner_os} - no special system dependencies needed"
    fi
}

# Install project dependencies
install_project() {
    local python_version=$1
    local engine_name=$2

    log_info "Installing base dependencies..."
    uv sync -p "$python_version" --no-dev --group test

    if [[ "$engine_name" == scipy_* ]]; then
        log_info "Installing scipy extra..."
        uv sync -p "$python_version" --no-dev --group test --extra scipy
    fi

    if [[ "$engine_name" == cythonized_* ]]; then
        log_info "Building Cython extensions..."
        uv sync -p "$python_version" --no-dev --group test --extra exts
    fi
}

# Run tests with retry logic
run_tests() {
    local test_path=$1
    local engine_name=$2
    local exit_code=0

    log_info "Running tests from ${test_path} with engine ${engine_name}..."
    
    # First attempt with parallel execution
    pytest "$test_path" --no-header -v -n auto --engine="$engine_name" || exit_code=$?

    if [ $exit_code -ne 0 ]; then
        log_warn "Pytest failed on the first attempt (Code: ${exit_code})"
        log_warn "Running again without parallel execution for detailed output..."
        pytest "$test_path" -v -s -q --engine="$engine_name"
    else
        log_info "Pytest succeeded on the first attempt"
    fi
}

# Run stress tests with optional Valgrind
run_stress_tests() {
    local normal_exit_code=0

    log_info "psutil required, installing..."
    uv pip install psutil
    
    log_info "Running stress tests normally..."
    pytest ./py_ballisticcalc.exts/tests -m stress || normal_exit_code=$?

    if [ $normal_exit_code -ne 0 ]; then
        log_error "Normal stress tests FAILED. Installing Valgrind and rerunning with memory check..."
        
        if ! command -v valgrind &> /dev/null; then
            log_info "Installing Valgrind..."
            sudo apt update
            sudo apt install -y valgrind
        fi

        LOG_FILE="valgrind.log"
        log_info "Log will be visible in the console AND saved to ${LOG_FILE}"
        
        valgrind \
            --tool=memcheck \
            --leak-check=full \
            --show-leak-kinds=all \
            --track-origins=yes \
            -- \
            pytest ./py_ballisticcalc.exts/tests -m stress \
            2>&1 | tee ${LOG_FILE}
    else
        log_info "Stress tests passed"
    fi
}

# Main command dispatcher
case "${1:-}" in
    install-system-deps)
        install_system_deps "${2:-3.10}" "${3:-Linux}"
        ;;
    install-project)
        install_project "${2:-3.10}" "${3:-euler_engine}"
        ;;
    test)
        run_tests "${2:-tests}" "${3:-euler_engine}"
        ;;
    stress)
        run_stress_tests
        ;;
    *)
        echo "Usage: $0 {install-system-deps|install-project|test|stress} [args...]"
        echo ""
        echo "Commands:"
        echo "  install-system-deps <python_version> <runner_os>  - Install system dependencies"
        echo "  install-project <python_version> <engine_name>   - Install project and its dependencies"
        echo "  test <test_path> <engine_name>                   - Run tests with retry logic"
        echo "  stress                                           - Run stress tests with Valgrind fallback"
        # exit 1
        ;;
esac