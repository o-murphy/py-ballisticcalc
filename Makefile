# Makefile

VENV_DIR = .venv

.PHONY: sync-dev sync-exts build-exts clean-exts clean \
        test-dev test-exts test-leaks bench-dev bench-exts

# -------------------------------------------------------------
# ENVIRONMENT TARGETS
# -------------------------------------------------------------

# Install/update pure Python dependencies only. Fast, no build.
sync-dev:
	@echo "--- Syncing dev environment ---"
	uv sync
	@echo "✅ Done. Activate with 'source $(VENV_DIR)/bin/activate'."

# Switch to exts without forcing a rebuild.
# Use this when .so files are already present and you just need the env updated.
sync-exts:
	@echo "--- Syncing exts environment (no rebuild) ---"
	uv sync --extra exts
	@echo "✅ Done. Use 'make build-exts' if you need a full rebuild."

# Full clean + submodule init + rebuild of Cython extensions.
# Use this after changing .pyx/.pxd/.cpp/.hpp files.
build-exts: clean-exts
	@echo "--- Initializing git submodules ---"
	git submodule update --init --recursive
	@echo "--- Building Cython extensions ---"
	uv sync --extra exts --reinstall-package py-ballisticcalc --reinstall-package py-ballisticcalc-exts
	@echo "✅ Extensions built."

# -------------------------------------------------------------
# CLEANUP TARGETS
# -------------------------------------------------------------

# Remove Cython build artifacts. Does NOT sync/install anything.
clean-exts:
	@echo "--- Removing extension build artifacts ---"
	-rm -rfv py_ballisticcalc_exts.egg-info
	-rm -rfv py_ballisticcalc.exts/py_ballisticcalc.exts.egg-info
	-rm -rfv py_ballisticcalc.exts/build
	-rm -rfv py_ballisticcalc.exts/py_ballisticcalc_exts.egg-info
	-rm -rfv py_ballisticcalc.exts/py_ballisticcalc_exts/build
	-find py_ballisticcalc.exts/py_ballisticcalc_exts/ -maxdepth 1 -type f \
		\( -name "*.pyd" -o -name "*.so" -o -name "*.html" \) -exec rm -v {} \;
	-find . -type d -name "build" -not -path "./.git/*" -exec rm -rfv {} +
	-find . -type d -name "dist" -not -path "./.git/*" -exec rm -rfv {} +
	@echo "--- Cleanup complete. ---"

# Remove the entire virtual environment and caches.
clean:
	@echo "--- Removing virtual environment and caches ---"
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" | xargs rm -rf

# -------------------------------------------------------------
# TESTING TARGETS
# -------------------------------------------------------------

# Pure Python tests. Only syncs dev env — no Cython build needed.
test-dev: sync-dev
	@echo "--- Testing pure Python engine ---"
	uv run pytest --engine="rk4_engine"

# Cythonized tests. Always does a full clean rebuild first.
test-exts: build-exts
	@echo "--- Testing Cythonized engine ---"
	uv run pytest py_ballisticcalc.exts --engine="cythonized_rk4_engine"
	uv run pytest --engine="cythonized_rk4_engine"

# Memory leak tests with valgrind (stress suite).
test-leaks: build-exts
	@echo "--- Valgrind memory leak check ---"
	ulimit -n 65536 && \
	valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all --track-origins=yes \
		-- uv run pytest -m stress ./py_ballisticcalc.exts 2> valgrind.log

# -------------------------------------------------------------
# BENCHMARKING TARGETS
# -------------------------------------------------------------

bench-dev: sync-dev
	@echo "--- Benchmarking pure Python engine ---"
	uv run python scripts/benchmark.py --engine="rk4_engine" -w 100 -r 1000

bench-exts: build-exts
	@echo "--- Benchmarking Cythonized engine ---"
	uv run python scripts/benchmark.py --engine="cythonized_rk4_engine" -w 100 -r 1000
