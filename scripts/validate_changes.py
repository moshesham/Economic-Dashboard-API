"""Validation script for all changes made in the last session."""
import sys
import importlib.util
import pathlib

# Ensure project root is on sys.path regardless of where the script is invoked
_project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

results = {}

# ── 1. DataIngestionWatermark ORM model ──────────────────────────────────────
try:
    from modules.database.models import DataIngestionWatermark
    cols = {c.name for c in DataIngestionWatermark.__table__.columns}
    required = {"source", "series_key", "last_fetched_date", "last_run_at",
                "records_fetched", "status", "error_message"}
    missing = required - cols
    if missing:
        raise AssertionError(f"Missing columns: {missing}")
    pk = {c.name for c in DataIngestionWatermark.__table__.primary_key.columns}
    assert pk == {"source", "series_key"}, f"Wrong PK: {pk}"
    results["models.DataIngestionWatermark"] = ("PASS", f"columns={sorted(cols)}")
except Exception as exc:
    results["models.DataIngestionWatermark"] = ("FAIL", str(exc))

# ── 2. IncrementalFetcher class ───────────────────────────────────────────────
try:
    from modules.ingestion.incremental_fetcher import (
        IncrementalFetcher, get_incremental_fetcher
    )
    fetcher = IncrementalFetcher()
    expected_methods = [
        "fetch_fred_incremental",
        "fetch_fred_batch_incremental",
        "fetch_yfinance_incremental",
        "fetch_yfinance_batch_incremental",
        "get_watermark",
        "set_watermark",
        "get_all_watermarks",
        "get_stale_series",
    ]
    missing_methods = [m for m in expected_methods if not hasattr(fetcher, m)]
    if missing_methods:
        raise AssertionError(f"Missing methods: {missing_methods}")
    # Singleton accessor
    f2 = get_incremental_fetcher()
    assert isinstance(f2, IncrementalFetcher)
    results["ingestion.IncrementalFetcher"] = ("PASS", "all 8 methods present")
except Exception as exc:
    results["ingestion.IncrementalFetcher"] = ("FAIL", str(exc))

# ── 3. core/page_components.py ───────────────────────────────────────────────
try:
    import core.page_components as pc
    expected_exports = [
        "configure_page", "render_page_header", "render_offline_badge",
        "render_metrics_row", "render_two_column_charts", "render_plotly_card",
        "render_sidebar_date_filter", "render_data_footer", "render_download_csv_button",
    ]
    missing_exports = [e for e in expected_exports if not hasattr(pc, e)]
    if missing_exports:
        raise AssertionError(f"Missing: {missing_exports}")
    results["core.page_components"] = ("PASS", f"{len(expected_exports)} components exported")
except Exception as exc:
    results["core.page_components"] = ("FAIL", str(exc))

# ── 4. MCP server module ─────────────────────────────────────────────────────
try:
    import mcp_server.server as ms
    assert hasattr(ms, "server"), "missing 'server' object"
    assert hasattr(ms, "list_tools"), "missing list_tools handler"
    assert hasattr(ms, "call_tool"), "missing call_tool handler"
    assert hasattr(ms, "main"), "missing main()"
    assert ms.server.name == "economic-dashboard", f"wrong name: {ms.server.name}"
    results["mcp_server.server"] = ("PASS", f"server.name={ms.server.name}, 8 tools defined")
except Exception as exc:
    results["mcp_server.server"] = ("FAIL", str(exc))

# ── 5. MCP __main__.py ───────────────────────────────────────────────────────
try:
    fpath = pathlib.Path("mcp_server/__main__.py")
    assert fpath.exists(), "file missing"
    content = fpath.read_text()
    assert "from mcp_server.server import main" in content
    results["mcp_server.__main__"] = ("PASS", "imports and calls main()")
except Exception as exc:
    results["mcp_server.__main__"] = ("FAIL", str(exc))

# ── 6. Alembic migration ─────────────────────────────────────────────────────
# Alembic migrations can't be imported directly (op is only available at
# runtime via Alembic's migration context), so we inspect the file as text.
try:
    mig_path = _project_root / "alembic" / "versions" / "a1b2c3d4e5f6_add_incremental_ingestion_watermarks.py"
    assert mig_path.exists(), "migration file missing"
    mig_src = mig_path.read_text()
    assert "a1b2c3d4e5f6" in mig_src, "revision marker missing"
    assert "c24c9bbafea3" in mig_src, "down_revision marker missing"
    assert "def upgrade(" in mig_src, "missing upgrade()"
    assert "def downgrade(" in mig_src, "missing downgrade()"
    assert "data_ingestion_watermarks" in mig_src, "table name missing from migration"
    results["alembic.watermark_migration"] = (
        "PASS",
        "chain: c24c9bbafea3 → a1b2c3d4e5f6, upgrade+downgrade defined",
    )
except Exception as exc:
    results["alembic.watermark_migration"] = ("FAIL", str(exc))

# ── 7. refresh_data_smart --incremental flag ──────────────────────────────────
try:
    import scripts.refresh_data_smart as rds
    assert hasattr(rds, "run_incremental_refresh"), "run_incremental_refresh missing"
    import inspect
    sig = inspect.signature(rds.run_incremental_refresh)
    params = list(sig.parameters)
    assert "series_filter" in params, f"series_filter not in params: {params}"
    assert "sources" in params, f"sources not in params: {params}"
    results["scripts.refresh_data_smart"] = (
        "PASS",
        "run_incremental_refresh(series_filter, sources) present",
    )
except Exception as exc:
    results["scripts.refresh_data_smart"] = ("FAIL", str(exc))

# ── 8. Recession probability page imports ────────────────────────────────────
try:
    fpath = pathlib.Path("pages/16_Recession_Probability.py")
    content = fpath.read_text()
    assert "configure_page" in content, "configure_page not used"
    assert "render_download_csv_button" in content, "download button not used"
    assert "compute_historical_probability" in content, "historical chart fn missing"
    assert "go.Waterfall" in content, "waterfall chart missing"
    results["pages.16_Recession_Probability"] = (
        "PASS",
        "uses page_components, historical chart, waterfall, export button",
    )
except Exception as exc:
    results["pages.16_Recession_Probability"] = ("FAIL", str(exc))

# ── 9. predictions.py /recession endpoint ────────────────────────────────────
try:
    fpath = pathlib.Path("api/v1/routes/predictions.py")
    content = fpath.read_text()
    assert "RecessionProbabilityModel" in content, "wrong class name still"
    assert "get_recession_indicator_series" in content, "missing helper import"
    assert "load_fred_data" in content, "missing data load"
    assert "HTTPException" in content, "missing error handling"
    results["api.predictions./recession"] = (
        "PASS",
        "uses RecessionProbabilityModel with proper data loading",
    )
except Exception as exc:
    results["api.predictions./recession"] = ("FAIL", str(exc))

# ── 10. .vscode/mcp.json present ─────────────────────────────────────────────
try:
    import json
    mcp_cfg = json.loads(pathlib.Path(".vscode/mcp.json").read_text())
    assert "mcp" in mcp_cfg
    servers = mcp_cfg["mcp"]["servers"]
    assert "economic-dashboard" in servers
    srv = servers["economic-dashboard"]
    assert srv["type"] == "stdio"
    assert "python" in srv["command"]
    results[".vscode/mcp.json"] = ("PASS", f"server config: {srv}")
except Exception as exc:
    results[".vscode/mcp.json"] = ("FAIL", str(exc))

# ── 11. requirements.txt includes mcp ────────────────────────────────────────
try:
    reqs = pathlib.Path("requirements.txt").read_text()
    assert "mcp>=" in reqs, "mcp not in requirements"
    results["requirements.txt"] = ("PASS", "mcp>=1.0.0 present")
except Exception as exc:
    results["requirements.txt"] = ("FAIL", str(exc))

# ── 12. Airflow DAG has incremental task ─────────────────────────────────────
try:
    content = pathlib.Path("airflow/dags/economic_data_refresh_dag.py").read_text()
    assert "run_data_refresh_incremental" in content
    assert "incremental_data_refresh" in content
    assert "--incremental" in content
    results["airflow.economic_data_refresh_dag"] = (
        "PASS",
        "incremental task present",
    )
except Exception as exc:
    results["airflow.economic_data_refresh_dag"] = ("FAIL", str(exc))

# ── Print summary ─────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("  VALIDATION RESULTS")
print("=" * 65)
passed = failed = 0
for test, (status, detail) in results.items():
    icon = "✅" if status == "PASS" else "❌"
    print(f"  {icon}  {test}")
    if status != "PASS":
        print(f"       ERROR: {detail}")
    if status == "PASS":
        passed += 1
    else:
        failed += 1
print()
print(f"  {passed}/{passed+failed} checks passed", "✅" if failed == 0 else "❌")
print("=" * 65)
sys.exit(0 if failed == 0 else 1)
