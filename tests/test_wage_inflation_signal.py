"""Tests for wage-inflation pass-through feature engineering."""

import numpy as np
import pandas as pd

from modules.features.wage_inflation_signal import (
    build_wage_inflation_pass_through_features,
)


def _make_inputs(periods: int = 48):
    idx = pd.date_range("2020-01-01", periods=periods, freq="MS")

    bls = pd.DataFrame(
        {
            "CES0500000003": np.linspace(25.0, 31.0, periods),
            "CES0500000007": np.linspace(34.0, 35.5, periods),
            "CIS2010000000000I": np.linspace(100.0, 118.0, periods),
            "PRS85006093": np.linspace(100.0, 111.0, periods),
        },
        index=idx,
    )

    inflation = pd.DataFrame(
        {
            "CPILFESL": np.linspace(250.0, 294.0, periods),
            "PPIFGS": np.linspace(200.0, 246.0, periods),
        },
        index=idx,
    )

    return bls, inflation


def test_build_wage_inflation_features_has_expected_columns():
    bls, inflation = _make_inputs()
    features = build_wage_inflation_pass_through_features(bls, inflation)

    assert not features.empty
    expected = {
        "unit_labor_cost_proxy",
        "ulc_proxy_yoy",
        "wage_minus_productivity_accel",
        "wage_pressure_composite",
        "core_cpi_yoy",
        "ppi_yoy",
        "core_cpi_fwd_3m_ann",
        "core_cpi_fwd_6m_ann",
        "core_cpi_fwd_12m_ann",
        "corr_wage_pressure_core_cpi_fwd_6m",
    }
    for col in expected:
        assert col in features.columns


def test_unit_labor_cost_proxy_formula_matches_definition():
    bls, inflation = _make_inputs()
    features = build_wage_inflation_pass_through_features(bls, inflation)

    check_date = features.dropna(subset=["unit_labor_cost_proxy"]).index[10]
    expected = (
        bls.loc[check_date, "CES0500000003"]
        * bls.loc[check_date, "CES0500000007"]
        / bls.loc[check_date, "PRS85006093"]
    ) * 100.0

    assert np.isclose(features.loc[check_date, "unit_labor_cost_proxy"], expected, rtol=1e-9)


def test_returns_empty_when_required_inputs_missing():
    bls, inflation = _make_inputs()
    bad_bls = bls.drop(columns=["PRS85006093"])

    features = build_wage_inflation_pass_through_features(bad_bls, inflation)
    assert features.empty
