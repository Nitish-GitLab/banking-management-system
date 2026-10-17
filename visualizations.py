"""Plotly figure builders. Each function takes a DataFrame and returns a figure
(no Streamlit calls here, so charts stay reusable and easy to reason about)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import config as cfg
import data_processing as dp

NAVY, BLUE, MID, LIGHT, GOLD = "#0B1F3A", "#1F4E8C", "#4A7DB8", "#9DB7D9", "#C9A227"
COLORWAY = [BLUE, GOLD, MID, NAVY, LIGHT, "#6B7A90", "#8FA8C8", "#A68B1F"]
FONT = "Segoe UI, Arial, sans-serif"


def _style(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=16, color=NAVY)),
        template="plotly_white",
        font=dict(family=FONT, size=12, color="#1B2A41"),
        margin=dict(l=10, r=10, t=55, b=10),
        height=height,
        colorway=COLORWAY,
        legend=dict(title=None),
    )
    return fig


def _empty(title: str, message: str = "No data available for this selection") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=14, color="#6B7A90"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, title, height=300)


# ----------------------------------------------------------------------------
# Categorical charts
# ----------------------------------------------------------------------------
def bar_counts(df, col, title, horizontal=False, top_n=None, sort="count"):
    if df.empty:
        return _empty(title)
    data = dp.count_by(df, col, top_n=top_n, sort=sort)
    order = data[col].tolist()
    if horizontal:
        fig = px.bar(data.iloc[::-1], x="Records", y=col, orientation="h", text="Records", custom_data=["Share %"])
        cat, val = "%{y}", "%{x:,}"
        fig.update_yaxes(type="category", categoryorder="array", categoryarray=order[::-1], title_text=None)
    else:
        fig = px.bar(data, x=col, y="Records", text="Records", custom_data=["Share %"])
        cat, val = "%{x}", "%{y:,}"
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=order)
    fig.update_traces(
        marker_color=BLUE, texttemplate="%{text:,}", textposition="outside", cliponaxis=False,
        hovertemplate=f"{col}: {cat}<br>Records: {val}<br>Share: " + "%{customdata[0]:.1f}%<extra></extra>",
    )
    return _style(fig, title, height=max(340, 28 * len(data) + 120) if horizontal else 380)


def donut(df, col, title, top_n=8):
    if df.empty:
        return _empty(title)
    data = dp.count_by(df, col, top_n=top_n, group_other=True, sort="label" if col == cfg.COL_INCOME_BAND else "count")
    fig = px.pie(data, names=col, values="Records", hole=0.55)
    fig.update_traces(sort=False, textinfo="percent", marker=dict(line=dict(color="#FFFFFF", width=2)),
                      hovertemplate="%{label}<br>Records: %{value:,}<br>Share: %{percent}<extra></extra>")
    return _style(fig, title)


def stacked_share(df, cat, hue, title):
    """100% stacked bars: how each `hue` value is distributed inside every `cat` value."""
    if df.empty:
        return _empty(title)
    x = dp.to_label(df[cat]).astype(str).rename(cat)
    h = dp.to_label(df[hue]).astype(str).rename(hue)
    ct = pd.crosstab(x, h, normalize="index") * 100
    ct = ct.reindex(dp.order_labels(ct.index, cat))
    ct = ct[dp.order_labels(ct.columns, hue)]
    long = ct.reset_index().melt(id_vars=cat, var_name=hue, value_name="Share %")
    fig = px.bar(long, x=cat, y="Share %", color=hue, barmode="stack")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=list(ct.index))
    fig.update_yaxes(ticksuffix="%", range=[0, 100])
    fig.update_traces(hovertemplate=f"{cat}: %{{x}}<br>{hue}: %{{fullData.name}}<br>Share: %{{y:.1f}}%<extra></extra>")
    return _style(fig, title)


# ----------------------------------------------------------------------------
# Numeric charts
# ----------------------------------------------------------------------------
def histogram(df, col, title, nbins=40, log_x=False):
    data = df[[col]].dropna()
    if log_x:
        data = data[data[col] > 0]
    if data.empty:
        return _empty(title, "No values to plot (log scale needs positive values)" if log_x else "No values to plot")
    fig = px.histogram(data, x=col, nbins=nbins, log_x=log_x)
    fig.update_traces(marker_color=BLUE)
    fig.update_yaxes(title_text="Records")
    fig.update_xaxes(tickformat="~s")
    if not log_x:
        median = float(data[col].median())
        fig.add_vline(x=median, line_dash="dash", line_color=GOLD,
                      annotation_text=f"Median {median:,.0f}", annotation_position="top right")
    return _style(fig, title)


def box_by_category(df, cat, num, title, top_n=10):
    work = pd.DataFrame({cat: dp.to_label(df[cat]).astype(str), num: df[num]}).dropna(subset=[num])
    if work.empty:
        return _empty(title)
    top = dp.count_by(df, cat, top_n=top_n, sort="label" if cat == cfg.COL_INCOME_BAND else "count")[cat].tolist()
    work = work[work[cat].isin(top)]
    fig = px.box(work, x=cat, y=num, points=False, category_orders={cat: top})
    fig.update_traces(marker_color=BLUE)
    fig.update_xaxes(type="category")
    fig.update_yaxes(tickformat="~s")
    return _style(fig, title)


def grouped_values(df, group_col, value_cols, title, agg="mean", top_n=12):
    """Side-by-side bars of the average (or total) of several measures per group."""
    if df.empty:
        return _empty(title)
    top = dp.count_by(df, group_col, top_n=top_n, sort="label" if group_col == cfg.COL_INCOME_BAND else "count")[group_col].tolist()
    work = df[value_cols].copy()
    work[group_col] = dp.to_label(df[group_col]).astype(str)
    work = work[work[group_col].isin(top)]
    grouped = work.groupby(group_col)[value_cols]
    summary = (grouped.sum(min_count=1) if agg == "sum" else grouped.agg(agg)).reset_index()
    value_name = "Average" if agg == "mean" else "Total"
    long = summary.melt(id_vars=group_col, var_name="Measure", value_name=value_name)
    fig = px.bar(long, x=group_col, y=value_name, color="Measure", barmode="group", category_orders={group_col: top})
    fig.update_xaxes(type="category")
    fig.update_yaxes(tickformat="~s")
    fig.update_traces(hovertemplate=f"{group_col}: %{{x}}<br>%{{fullData.name}}<br>{value_name}: %{{y:,.0f}}<extra></extra>")
    return _style(fig, title)


def totals_bar(df, cols, title):
    totals = pd.DataFrame({"Measure": cols, "Total": [df[c].sum(min_count=1) for c in cols]}).dropna()
    if totals.empty:
        return _empty(title)
    fig = px.bar(totals.iloc[::-1], x="Total", y="Measure", orientation="h", text="Total")
    fig.update_traces(marker_color=BLUE, texttemplate="%{x:.3s}", textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}<br>Total: %{x:,.0f}<extra></extra>")
    fig.update_xaxes(tickformat="~s")
    fig.update_yaxes(title_text=None)
    return _style(fig, title, height=320)


def ratio_bar(ratio_df, title):
    if ratio_df.empty:
        return _empty(title, f"No group has at least {cfg.MIN_GROUP_SIZE} records with positive deposits")
    data = ratio_df.head(15).iloc[::-1]
    fig = px.bar(data, x="Loan-to-deposit ratio", y="Group", orientation="h", custom_data=["Records"])
    fig.update_traces(marker_color=BLUE,
                      hovertemplate="%{y}<br>Loans / deposits: %{x:.2f}<br>Records: %{customdata[0]:,}<extra></extra>")
    fig.update_yaxes(title_text=None, type="category")
    return _style(fig, title, height=max(320, 28 * len(data) + 120))


def scatter(df, x, y, title, color=None):
    cols = [x, y] + ([color] if color else [])
    work = df[cols].dropna(subset=[x, y]).copy()
    if work.empty:
        return _empty(title)
    if color:
        work[color] = dp.to_label(work[color]).astype(str)
    fig = px.scatter(work, x=x, y=y, color=color, opacity=0.55)
    fig.update_xaxes(tickformat="~s")
    fig.update_yaxes(tickformat="~s")
    return _style(fig, title, height=420)


def correlation_heatmap(df, cols, title):
    usable = [c for c in cols if df[c].nunique(dropna=True) > 1]
    if len(usable) < 2:
        return _empty(title, "Need at least two numeric columns with variation")
    corr = df[usable].corr()
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto")
    fig.update_xaxes(tickangle=-40)
    fig.update_layout(coloraxis_colorbar=dict(title="r"))
    return _style(fig, title, height=520)
