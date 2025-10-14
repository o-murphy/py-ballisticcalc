# Makefile

# Define the virtual environment directory
VENV_DIR = .venv

# Define the uv command (uv is often preferred as a standalone tool)
UV = uv

# Activation script logic is intentionally omitted here as it must be run 
# manually in the main shell (e.g., source .venv/bin/activate).

# Phony targets are actions, not files
.PHONY: sync-dev sync-exts clean-exts clean test-dev test-exts bench-dev bench-exts

# -------------------------------------------------------------
# CORE SYNC TARGETS
# -------------------------------------------------------------

# Target 1: Standard development sync
# Action: Runs uv sync --dev to install base dependencies.
sync-dev:
	@echo "--- Running standard dev sync (uv sync --dev) ---"
	$(UV) sync --dev
	@echo "✅ Dev sync complete. Activate with 'source $(VENV_DIR)/bin/activate'."

# Target 2: Full sync with cleanup and extras
# Prerequisites: clean-exts must run first.
# Action: Runs uv sync --dev --extra exts --no-cache to install extensions.
sync-exts: clean-exts
	@echo "--- Running full sync with extras and no-cache ---"
	$(UV) sync --dev --extra exts --no-cache
	@echo "✅ Exts sync complete. Activate with 'source $(VENV_DIR)/bin/activate'."

# -------------------------------------------------------------
# CLEANUP TARGETS
# -------------------------------------------------------------

# Cleanup target for external build artifacts.
# Prerequisites: sync-dev must run first to ensure the base environment is available.
# Action: Removes various build/cache directories and runs a custom cleanup script.
# The hyphen (-) ignores errors if files/dirs don't exist during removal.
clean-exts: sync-dev
	@echo "--- Removing build artifacts for extensions (VERBOSE) ---"
	
	# 1. REMOVE SPECIFIC BUILD ARTIFACT DIRECTORIES (Non-source)
	# Use -rm -rfv for verbose output when deleting these specific directories.
	-rm -rfv py_ballisticcalc_exts.egg-info
	-rm -rfv py_ballisticcalc.exts/py_ballisticcalc.exts.egg-info
	-rm -rfv py_ballisticcalc.exts/build
	-rm -rfv py_ballisticcalc.exts/py_ballisticcalc_exts.egg-info
	-rm -rfv py_ballisticcalc.exts/py_ballisticcalc_exts/build
	
	# 2. REMOVE GENERATED FILES (Cython .c, .h, .html, .pyd files)
	# Use -exec rm -v {} \; to output each deleted file. Maxdepth 1 protects src/ and include/.
	@echo "Searching for generated files in py_ballisticcalc_exts/..."
	-find py_ballisticcalc_exts/ -maxdepth 1 -type f \( -name "*.c" -o -name "*.h" -o -name "*.pyd" -o -name "*.html" \) -exec rm -v {} \;
	-find py_ballisticcalc.exts/py_ballisticcalc_exts/ -maxdepth 1 -type f \( -name "*.pyd" -o -name "*.html" \) -exec rm -v {} \;

	# 3. REMOVE GENERAL BUILD/EGG-INFO ARTIFACTS (Recursive find cleanup)
	# Use -exec rm -rfv {} + for verbose output when deleting general build/dist directories.
	@echo "Searching for general build/dist directories..."
	-find . -type d -name "build" -exec rm -rfv {} +
	-find . -type d -name "dist" -exec rm -rfv {} +
	
	@echo "--- Cleanup complete. ---"

# Cleanup for the entire environment
# Action: Removes the virtual environment directory and all __pycache__ directories.
clean:
	@echo "--- Removing virtual environment and cache ---"
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" | xargs rm -rf

# -------------------------------------------------------------
# TESTING TARGETS
# -------------------------------------------------------------

# Target 3: Test base environment
# Prerequisites: clean-exts must run first (which pulls in sync-dev).
# Action: Runs pytest using the base 'rk4_engine'.
test-dev: clean-exts
	@echo "--- Testing the Development/Base environment (pure Python engine) ---"
	${UV} run pytest --engine="rk4_engine"

# Target 4: Test extensions environment
# Prerequisites: sync-exts must run first (which pulls in clean-exts and sync-dev).
# Action: Runs pytest twice using the 'cythonized_rk4_engine'.
test-exts: sync-exts
	@echo "--- Testing the Extensions environment (pure Python engine) ---"
	${UV} run pytest py_ballisticcalc.exts --engine="cythonized_rk4_engine"
	${UV} run pytest --engine="cythonized_rk4_engine"


# -------------------------------------------------------------
# BENCHMARKING TARGETS
# -------------------------------------------------------------

# Target: bench-dev
# Prerequisites: sync-dev must be complete (ensures base dependencies are installed).
# Action: Runs the benchmark script, testing the pure Python engine.
bench-dev: sync-dev
	@echo "--- Benchmarking the Development/Base environment (pure Python engine) ---"
	${UV} run python scripts/benchmark.py --engine="rk4_engine" 

# Target: bench-exts
# Prerequisites: sync-exts must be complete (ensures extensions are built and installed).
# Action: Runs the benchmark script, testing the high-performance Cythonized engine.
bench-exts: sync-exts
	@echo "--- Benchmarking the Extensions environment (Cythonized engine) ---"
	${UV} run python scripts/benchmark.py --engine="cythonized_rk4_engine"