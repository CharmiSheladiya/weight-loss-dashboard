"""
analytics.py
All Plotly chart construction lives here, kept separate from app.py so the
UI layer stays thin. Every function returns a ready-to-render go.Figure.

Color palette is centralized so charts feel consistent with the rest of
the app's design system (see app.py CUSTOM_CSS for matching hex values).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import utils

# ---------------------------------------------------------------------------
# Design tokens (kept in sync with app.py's CSS theme)
# ---------------------------------------------------------------------------

COLOR_PRIMARY = "#2E5077"      # deep teal-blue
COLOR_ACCENT = "#4FB286"       # fresh green (progress / good)
COLOR_WARNING = "#E8A33D"      # amber (caution)
COLOR_DANGER = "#D9534F"       # red (behind / alert)
COLOR_GOAL = "#9B5DE5"         # violet (goal line)
COLOR_MUTED = "#9AA5B1"        # grey (secondary series)
COLOR_BG = "#FFFFFF"
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"

BASE_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, size=13, color="#1F2937"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=20, t=50, b=40),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor="rgba(0,0,0,0)",
    ),
)


def _empty_figure(message: str = "No data logged yet. Add entries in Daily Tracker.") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color=COLOR_MUTED),
    )
    fig.update_layout(**BASE_LAYOUT, height=320, xaxis_visible=False, yaxis_visible=False)
    return fig


# ---------------------------------------------------------------------------
# Weight trend
# ---------------------------------------------------------------------------

def weight_trend_chart(df: pd.DataFrame, goal_weight: float) -> go.Figure:
    if df is None or df.empty or df["weight_kg"].dropna().empty:
        return _empty_figure()

    w = df.dropna(subset=["weight_kg"]).sort_values("log_date")
    rolling7 = utils.rolling_average(df, "weight_kg", 7)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=w["log_date"], y=w["weight_kg"],
            mode="markers+lines",
            name="Daily Weight",
            line=dict(color=COLOR_MUTED, width=1.5),
            marker=dict(size=6, color=COLOR_PRIMARY),
            opacity=0.85,
        )
    )
    if not rolling7.empty:
        fig.add_trace(
            go.Scatter(
                x=rolling7["log_date"], y=rolling7["weight_kg"],
                mode="lines",
                name="7-Day Avg",
                line=dict(color=COLOR_ACCENT, width=3),
            )
        )
    fig.add_hline(
        y=goal_weight,
        line_dash="dash",
        line_color=COLOR_GOAL,
        annotation_text=f"Goal: {goal_weight} kg",
        annotation_position="top left",
    )
    fig.update_layout(
        **BASE_LAYOUT,
        title="Weight Trend",
        yaxis_title="Weight (kg)",
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# Weekly / Monthly trend (generic, reusable for weight/steps/calories)
# ---------------------------------------------------------------------------

def weekly_trend_chart(df: pd.DataFrame, column: str, label: str, color: str = COLOR_PRIMARY) -> go.Figure:
    weekly = utils.weekly_average(df, column)
    if weekly.empty:
        return _empty_figure()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=weekly["week_start"], y=weekly[column],
            name=f"Weekly Avg {label}",
            marker_color=color,
        )
    )
    fig.update_layout(
        **BASE_LAYOUT,
        title=f"Weekly {label} Trend",
        yaxis_title=label,
        height=340,
    )
    return fig


def monthly_trend_chart(df: pd.DataFrame, column: str, label: str, color: str = COLOR_PRIMARY) -> go.Figure:
    monthly = utils.monthly_average(df, column)
    if monthly.empty:
        return _empty_figure()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly["month_start"], y=monthly[column],
            name=f"Monthly Avg {label}",
            marker_color=color,
        )
    )
    fig.update_layout(
        **BASE_LAYOUT,
        title=f"Monthly {label} Trend",
        yaxis_title=label,
        height=340,
    )
    return fig


# ---------------------------------------------------------------------------
# Calories & Steps trend
# ---------------------------------------------------------------------------

def calories_trend_chart(df: pd.DataFrame, calorie_target: Optional[float] = None) -> go.Figure:
    if df is None or df.empty or df["calories"].dropna().empty:
        return _empty_figure()

    c = df.dropna(subset=["calories"]).sort_values("log_date")
    rolling7 = utils.rolling_average(df, "calories", 7)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=c["log_date"], y=c["calories"],
            name="Daily Calories",
            marker_color=COLOR_MUTED,
            opacity=0.6,
        )
    )
    if not rolling7.empty:
        fig.add_trace(
            go.Scatter(
                x=rolling7["log_date"], y=rolling7["calories"],
                mode="lines",
                name="7-Day Avg",
                line=dict(color=COLOR_WARNING, width=3),
            )
        )
    if calorie_target:
        fig.add_hline(
            y=calorie_target,
            line_dash="dash",
            line_color=COLOR_PRIMARY,
            annotation_text=f"Target: {int(calorie_target)} kcal",
            annotation_position="top left",
        )
    fig.update_layout(
        **BASE_LAYOUT,
        title="Calorie Intake Trend",
        yaxis_title="Calories (kcal)",
        height=360,
    )
    return fig


def steps_trend_chart(df: pd.DataFrame, steps_target: int = utils.STEPS_GOAL_DEFAULT) -> go.Figure:
    if df is None or df.empty or df["steps"].dropna().empty:
        return _empty_figure()

    s = df.dropna(subset=["steps"]).sort_values("log_date")
    rolling7 = utils.rolling_average(df, "steps", 7)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=s["log_date"], y=s["steps"],
            name="Daily Steps",
            marker_color=COLOR_ACCENT,
            opacity=0.65,
        )
    )
    if not rolling7.empty:
        fig.add_trace(
            go.Scatter(
                x=rolling7["log_date"], y=rolling7["steps"],
                mode="lines",
                name="7-Day Avg",
                line=dict(color=COLOR_PRIMARY, width=3),
            )
        )
    fig.add_hline(
        y=steps_target,
        line_dash="dash",
        line_color=COLOR_WARNING,
        annotation_text=f"Target: {steps_target}",
        annotation_position="top left",
    )
    fig.update_layout(
        **BASE_LAYOUT,
        title="Steps Trend",
        yaxis_title="Steps",
        height=360,
    )
    return fig


# ---------------------------------------------------------------------------
# Goal projection chart (actual vs ideal vs predicted)
# ---------------------------------------------------------------------------

def goal_projection_chart(
    df: pd.DataFrame,
    start_weight: float,
    start_date: date,
    goal_weight: float,
    target_date: date,
    predicted_weight: float,
) -> go.Figure:
    fig = go.Figure()

    # Ideal linear path
    ideal_x = [start_date, target_date]
    ideal_y = [start_weight, goal_weight]
    fig.add_trace(
        go.Scatter(
            x=ideal_x, y=ideal_y,
            mode="lines",
            name="Ideal Path",
            line=dict(color=COLOR_MUTED, width=2, dash="dot"),
        )
    )

    # Actual logged weight
    if df is not None and not df.empty and not df["weight_kg"].dropna().empty:
        actual = df.dropna(subset=["weight_kg"]).sort_values("log_date")
        fig.add_trace(
            go.Scatter(
                x=actual["log_date"], y=actual["weight_kg"],
                mode="lines+markers",
                name="Actual Weight",
                line=dict(color=COLOR_PRIMARY, width=3),
                marker=dict(size=5),
            )
        )
        last_actual_date = actual["log_date"].max()
        last_actual_weight = actual.iloc[-1]["weight_kg"]
    else:
        last_actual_date = pd.Timestamp(start_date)
        last_actual_weight = start_weight

    # Predicted projection from last actual point to target date
    fig.add_trace(
        go.Scatter(
            x=[last_actual_date, pd.Timestamp(target_date)],
            y=[last_actual_weight, predicted_weight],
            mode="lines+markers",
            name="Predicted Trajectory",
            line=dict(color=COLOR_WARNING, width=3, dash="dash"),
            marker=dict(size=7),
        )
    )

    # Goal marker
    fig.add_trace(
        go.Scatter(
            x=[pd.Timestamp(target_date)], y=[goal_weight],
            mode="markers",
            name="Goal",
            marker=dict(size=14, color=COLOR_ACCENT, symbol="star"),
        )
    )

    fig.update_layout(
        **BASE_LAYOUT,
        title="Goal Projection: Actual vs Ideal vs Predicted",
        yaxis_title="Weight (kg)",
        height=420,
    )
    return fig


# ---------------------------------------------------------------------------
# Target vs Actual comparison (KPI-style bullet chart for dashboard)
# ---------------------------------------------------------------------------

def target_vs_actual_gauge(current_weight: float, expected_weight: float, goal_weight: float) -> go.Figure:
    """A compact gauge comparing current weight to the ideal expected weight today."""
    lo = min(goal_weight, current_weight, expected_weight) - 2
    hi = max(goal_weight, current_weight, expected_weight) + 2

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=current_weight,
            delta={
                "reference": expected_weight,
                "decreasing": {"color": COLOR_ACCENT},
                "increasing": {"color": COLOR_DANGER},
            },
            number={"suffix": " kg", "font": {"size": 30}},
            title={"text": "Actual vs Expected Today", "font": {"size": 14}},
            gauge={
                "axis": {"range": [lo, hi]},
                "bar": {"color": COLOR_PRIMARY},
                "steps": [
                    {"range": [lo, expected_weight], "color": "#E5F3EC"},
                    {"range": [expected_weight, hi], "color": "#FBEAEA"},
                ],
                "threshold": {
                    "line": {"color": COLOR_GOAL, "width": 4},
                    "thickness": 0.85,
                    "value": goal_weight,
                },
            },
        )
    )
    layout = {**BASE_LAYOUT, "margin": dict(l=20, r=20, t=50, b=10)}
    fig.update_layout(**layout, height=260)
    return fig


# ---------------------------------------------------------------------------
# Multi-metric overview (small multiples) for Reports tab
# ---------------------------------------------------------------------------

def metrics_overview_chart(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return _empty_figure()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Weight (kg)", "Steps", "Calories", "Walking Minutes"),
        vertical_spacing=0.18,
        horizontal_spacing=0.1,
    )

    def add_series(row, col, column, color):
        sub = df.dropna(subset=[column]).sort_values("log_date")
        if sub.empty:
            return
        fig.add_trace(
            go.Scatter(
                x=sub["log_date"], y=sub[column],
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=4),
                showlegend=False,
            ),
            row=row, col=col,
        )

    add_series(1, 1, "weight_kg", COLOR_PRIMARY)
    add_series(1, 2, "steps", COLOR_ACCENT)
    add_series(2, 1, "calories", COLOR_WARNING)
    add_series(2, 2, "walking_minutes", COLOR_GOAL)

    fig.update_layout(
        **BASE_LAYOUT,
        height=520,
        title="Metrics Overview",
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Water & Protein progress (small donut-style indicators)
# ---------------------------------------------------------------------------

def daily_goal_donut(value: float, goal: float, label: str, unit: str, color: str) -> go.Figure:
    value = value or 0
    goal = goal or 1
    pct = min(100, round((value / goal) * 100)) if goal else 0

    fig = go.Figure(
        go.Pie(
            values=[pct, max(0, 100 - pct)],
            hole=0.72,
            marker=dict(colors=[color, "#EEF1F4"]),
            textinfo="none",
            sort=False,
            direction="clockwise",
        )
    )
    fig.add_annotation(
        text=f"<b>{int(value)}</b><br><span style='font-size:11px'>{unit} of {int(goal)}</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(size=15, color="#1F2937"),
    )
    layout = {**BASE_LAYOUT, "margin": dict(l=10, r=10, t=40, b=10)}
    fig.update_layout(
        **layout,
        title=label,
        height=220,
        showlegend=False,
    )
    return fig
