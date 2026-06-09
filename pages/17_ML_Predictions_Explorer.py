"""ML Predictions Explorer.

Small local-first tool to inspect single-horizon and multi-horizon
predictions using the currently available trained models.
"""

import streamlit as st
import pandas as pd

from modules.ml import MultiHorizonPredictor, PredictionEngine


st.set_page_config(page_title="ML Predictions Explorer", page_icon="📈", layout="wide")
st.title("📈 ML Predictions Explorer")
st.caption("Inspect single-horizon and multi-horizon stock predictions locally.")

with st.sidebar:
    st.header("Prediction Settings")
    ticker = st.text_input("Ticker", value="AAXJ").strip().upper()
    model_type = st.selectbox("Model", ["xgboost", "lightgbm", "ensemble"], index=0)
    include_explanation = st.checkbox("Include explanation", value=False)
    run_button = st.button("Run prediction", type="primary")


def _as_dataframe(items):
    if not items:
        return pd.DataFrame()
    return pd.DataFrame(items)


if run_button:
    if not ticker:
        st.error("Enter a ticker symbol.")
        st.stop()

    predictor = MultiHorizonPredictor()
    engine = PredictionEngine()

    try:
        single = engine.predict(
            ticker=ticker,
            model_type=model_type,
            store_result=True,
            horizon_days=5,
        )
        horizons = predictor.predict_all_horizons(
            ticker=ticker,
            model_type=model_type,
            include_explanation=include_explanation,
            store_result=True,
        )

        st.subheader("Single Horizon")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Direction", single.get("prediction_label", "N/A"))
        c2.metric("Confidence", f"{single.get('confidence', 0.0):.2%}")
        c3.metric("Probability Up", f"{single.get('probability_up', 0.0):.2%}")
        c4.metric("Target Date", single.get("target_date", "N/A"))

        st.subheader("Multi Horizon")
        horizon_rows = []
        for horizon, payload in horizons.get("horizons", {}).items():
            horizon_rows.append({
                "horizon": horizon,
                "direction": payload.get("direction"),
                "confidence": payload.get("confidence"),
                "probability_up": payload.get("probability_up"),
                "target_date": payload.get("target_date"),
            })
        st.dataframe(pd.DataFrame(horizon_rows), width="stretch", hide_index=True)

        st.write(f"**Consistency:** {horizons.get('consistency')}")
        st.write(f"**Overall confidence:** {horizons.get('overall_confidence', 0.0):.2%}")

        if include_explanation:
            st.subheader("Explanation")
            explanation = horizons.get("explanation", [])
            st.dataframe(_as_dataframe(explanation), width="stretch", hide_index=True)

        st.subheader("Recent Stored Predictions")
        history = engine.get_historical_predictions(ticker=ticker, prediction_type=model_type)
        if history.empty:
            st.info("No stored history found yet. Run a prediction first.")
        else:
            st.dataframe(history, width="stretch", hide_index=True)

    except Exception as exc:
        st.error(f"Prediction failed: {exc}")
        st.stop()

else:
    st.info("Choose a ticker and run the prediction to see horizons, explanations, and stored history.")
