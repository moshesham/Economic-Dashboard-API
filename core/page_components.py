"""
Shared page components for Streamlit dashboard pages.

All presentational patterns that were duplicated 10–50 times across
16 dashboard pages are consolidated here so updates happen in one place.

Usage
-----
    from core.page_components import (
        configure_page,
        render_page_header,
        render_offline_badge,
        render_metrics_row,
        render_data_section_header,
        render_two_column_charts,
        render_data_footer,
        render_sidebar_date_filter,
        render_sidebar_connection_status,
    )
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.chart_utils import display_metric


# ---------------------------------------------------------------------------
# Page-level setup
# ---------------------------------------------------------------------------

def configure_page(
    title: str,
    icon: str = "📊",
    layout: str = "wide",
    sidebar_state: str = "auto",
) -> None:
    """
    Call ``st.set_page_config`` with consistent defaults.

    Must be the very first Streamlit call in a page script.
    """
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout,
        initial_sidebar_state=sidebar_state,
    )


def render_page_header(
    title: str,
    subtitle: str = "",
    icon: str = "",
    show_divider: bool = True,
) -> None:
    """Render a standard page title + optional subtitle + divider."""
    full_title = f"{icon} {title}".strip() if icon else title
    st.title(full_title)
    if subtitle:
        st.markdown(subtitle)
    if show_divider:
        st.divider()


# ---------------------------------------------------------------------------
# Connection / offline status
# ---------------------------------------------------------------------------

def render_offline_badge() -> None:
    """
    Show an inline status badge for online/offline mode.
    Reads ``is_offline_mode()`` from ``core.config``.
    """
    try:
        from core.config import is_offline_mode
        offline = is_offline_mode()
    except ImportError:
        offline = False

    if offline:
        st.info("🔌 **Offline Mode** — displaying cached data", icon="ℹ️")
    else:
        st.success("🌐 **Live Data** — connected to data sources", icon="✅")


def render_sidebar_connection_status() -> None:
    """Render the connection status widget inside the sidebar."""
    with st.sidebar:
        render_offline_badge()


# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------

def render_metrics_row(
    metrics: Sequence[dict[str, Any]],
    n_cols: int | None = None,
) -> None:
    """
    Render a horizontal row of ``st.metric`` cards.

    Each dict in *metrics* accepts the same kwargs as
    :func:`core.chart_utils.display_metric`:
    ``label``, ``value``, ``fmt``, ``prefix``, ``suffix``,
    ``delta``, ``delta_fmt``, ``delta_suffix``, ``delta_color``, ``help_text``.

    ``n_cols`` defaults to ``len(metrics)`` capped at 4.

    Example::

        render_metrics_row([
            {"label": "GDP", "value": 27.4, "suffix": "T", "delta": 2.8,
             "delta_suffix": "% YoY"},
            {"label": "Unemployment", "value": 3.8, "suffix": "%"},
        ])
    """
    n = len(metrics)
    if n == 0:
        return
    cols_count = n_cols or min(n, 4)
    columns = st.columns(cols_count)
    for idx, metric_kwargs in enumerate(metrics):
        col_idx = idx % cols_count
        with columns[col_idx]:
            display_metric(**metric_kwargs)


# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------

def render_data_section_header(title: str, description: str = "") -> None:
    """Render a consistently-styled section sub-header."""
    st.subheader(title)
    if description:
        st.caption(description)


# ---------------------------------------------------------------------------
# Chart layout helpers
# ---------------------------------------------------------------------------

def render_two_column_charts(
    left_fn,
    right_fn,
    gap: str = "medium",
) -> None:
    """
    Render two chart callables side-by-side in equal columns.

    Args:
        left_fn:  A zero-argument callable that renders the left chart.
        right_fn: A zero-argument callable that renders the right chart.
        gap:      Column gap ('small', 'medium', 'large').
    """
    col1, col2 = st.columns(2, gap=gap)
    with col1:
        left_fn()
    with col2:
        right_fn()


def render_plotly_card(
    fig: go.Figure,
    key: str | None = None,
) -> None:
    """Render a Plotly figure with standard dark theme and full width."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


# ---------------------------------------------------------------------------
# Date / time filter
# ---------------------------------------------------------------------------

def render_sidebar_date_filter(
    label: str = "Date range",
    default_years: int = 5,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Render a from/to date picker inside the sidebar and return the selection.

    Returns:
        (start_date, end_date) as ``pd.Timestamp``.
    """
    end_default = pd.Timestamp.today().normalize()
    start_default = end_default - pd.DateOffset(years=default_years)

    with st.sidebar:
        st.subheader("📅 " + label)
        start = st.date_input("From", value=start_default.date())
        end = st.date_input("To", value=end_default.date())

    return pd.Timestamp(start), pd.Timestamp(end)


# ---------------------------------------------------------------------------
# Data-source footer
# ---------------------------------------------------------------------------

def render_data_footer(
    series_descriptions: dict[str, str],
    source_name: str = "Federal Reserve Economic Data (FRED)",
) -> None:
    """
    Render the standard 'Data Series Tracked' footer found on every page.

    Args:
        series_descriptions: Mapping of {series_id: human-readable description}.
        source_name: Name of the upstream data provider.
    """
    st.divider()
    lines = ["**Data Series Tracked:**"]
    for sid, desc in series_descriptions.items():
        lines.append(f"- **{sid}**: {desc}")
    lines.append(f"\n*Data Source: {source_name}*")
    st.markdown("\n".join(lines))


# ---------------------------------------------------------------------------
# Download button
# ---------------------------------------------------------------------------

def render_download_csv_button(
    df: pd.DataFrame,
    filename: str = "data.csv",
    label: str = "⬇️ Download CSV",
) -> None:
    """Render a one-click CSV download button for a DataFrame."""
    if df is None or df.empty:
        return
    st.download_button(
        label=label,
        data=df.to_csv().encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )
