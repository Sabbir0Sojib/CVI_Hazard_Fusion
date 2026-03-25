# ============================================================
# CVI-HazardFusion — Makefile
# Usage: make <target>
# Default target: help
# ============================================================

PYTHON      := python
PIP         := pip
SRC_DIR     := src
OUTPUT_DIR  := outputs
NOTEBOOK    := notebooks/CVI_HazardFusion.ipynb

.PHONY: help setup auth risk-score maps clean validate

# ============================================================
# help — List all available targets (default)
# ============================================================
help:
	@echo ""
	@echo "CVI-HazardFusion — Available Makefile Targets"
	@echo "============================================================"
	@echo ""
	@echo "  make setup       Install all Python dependencies from requirements.txt"
	@echo "  make auth        Authenticate with Google Earth Engine"
	@echo "  make risk-score  Run full pipeline: ingest → DRS → maps → CSV"
	@echo "  make maps        Generate map outputs only (requires drs_results.csv)"
	@echo "  make validate    Run data validation checks on pipeline outputs"
	@echo "  make clean       Remove all generated outputs from outputs/ directory"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup && make auth && make risk-score"
	@echo ""

# ============================================================
# setup — Install all Python dependencies
# ============================================================
setup:
	@echo "[setup] Installing Python dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "[setup] Done. Run 'make auth' to authenticate with Google Earth Engine."

# ============================================================
# auth — Authenticate with Google Earth Engine
# ============================================================
auth:
	@echo "[auth] Launching Google Earth Engine authentication flow..."
	@echo "[auth] A browser window will open. Sign in with your Google account"
	@echo "[auth] that has Earth Engine access enabled."
	$(PYTHON) -c "import ee; ee.Authenticate()"
	@echo "[auth] Authentication complete. Run 'make risk-score' to run the pipeline."

# ============================================================
# risk-score — Run the full pipeline (ingest → DRS → outputs)
# ============================================================
risk-score:
	@echo "[risk-score] Starting full CVI-HazardFusion pipeline..."
	@mkdir -p $(OUTPUT_DIR)
	@echo "[risk-score] Step 1/4: Authenticating with GEE..."
	$(PYTHON) -c "import ee; ee.Initialize()"
	@echo "[risk-score] Step 2/4: Ingesting satellite data from GEE..."
	$(PYTHON) $(SRC_DIR)/ingest.py
	@echo "[risk-score] Step 3/4: Computing DRS and risk classification..."
	$(PYTHON) $(SRC_DIR)/model.py
	@echo "[risk-score] Step 4/4: Generating maps and analytics..."
	$(PYTHON) $(SRC_DIR)/visualize.py
	@echo ""
	@echo "[risk-score] Pipeline complete. Outputs written to $(OUTPUT_DIR)/"
	@echo "  - $(OUTPUT_DIR)/map_1_DRS.png"
	@echo "  - $(OUTPUT_DIR)/map_2_classification.png"
	@echo "  - $(OUTPUT_DIR)/analytics_charts.png"
	@echo "  - $(OUTPUT_DIR)/interactive_dashboard.html"
	@echo "  - $(OUTPUT_DIR)/drs_results.csv"

# ============================================================
# maps — Generate map outputs only (skips GEE ingestion)
# Requires: outputs/drs_results.csv to already exist
# ============================================================
maps:
	@echo "[maps] Generating map and chart outputs from existing drs_results.csv..."
	@if [ ! -f "$(OUTPUT_DIR)/drs_results.csv" ]; then \
		echo "[maps] ERROR: $(OUTPUT_DIR)/drs_results.csv not found."; \
		echo "[maps] Run 'make risk-score' first to generate the data."; \
		exit 1; \
	fi
	@mkdir -p $(OUTPUT_DIR)
	$(PYTHON) $(SRC_DIR)/visualize.py
	@echo "[maps] Map generation complete."

# ============================================================
# validate — Run data validation checks on pipeline outputs
# ============================================================
validate:
	@echo "[validate] Running validation checks on pipeline outputs..."
	@if [ ! -f "$(OUTPUT_DIR)/drs_results.csv" ]; then \
		echo "[validate] ERROR: $(OUTPUT_DIR)/drs_results.csv not found. Run 'make risk-score' first."; \
		exit 1; \
	fi
	$(PYTHON) -c "\
import pandas as pd; \
df = pd.read_csv('$(OUTPUT_DIR)/drs_results.csv'); \
print(f'[validate] Districts loaded: {len(df)}'); \
assert len(df) == 64, f'Expected 64 districts, got {len(df)}'; \
assert df['DRS'].between(0, 100).all(), 'DRS values out of [0,100] range'; \
assert df['risk_level'].isin(['Critical','High','Moderate','Low']).all(), 'Invalid risk_level values'; \
print('[validate] DRS range: OK (all values in [0, 100])'); \
print('[validate] Risk levels: OK (all valid categories)'); \
print('[validate] District count: OK (64 districts)'); \
print(df['risk_level'].value_counts().to_string()); \
print('[validate] All checks passed.'); \
"
	@echo "[validate] Validation complete."

# ============================================================
# clean — Remove all generated outputs
# ============================================================
clean:
	@echo "[clean] Removing all generated outputs from $(OUTPUT_DIR)/..."
	@rm -rf $(OUTPUT_DIR)/*.png $(OUTPUT_DIR)/*.html $(OUTPUT_DIR)/*.csv
	@echo "[clean] Removing Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "[clean] Done. Run 'make risk-score' to regenerate all outputs."
