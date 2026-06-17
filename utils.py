"""
utils.py
Shared utility functions: date math, BMI, the Smart Goal Engine, recommendation
logic, consistency/progress scoring, and CSV/Excel export helpers.

Kept dependency-light (pandas + numpy only) so it can be unit-tested without
spinning up Streamlit.
"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KCAL_PER_KG_FAT = 7700.0  # approx. energy density of human adipose tissue
WATER_GOAL_ML_DEFAULT = 2500.0
PROTEIN_GOAL_G_DEFAULT = 75.0
STEPS_GOAL_DEFAULT = 7000  # mild knee pain -> moderate, joint-friendly target
WALK_MIN_GOAL_DEFAULT = 30


# ---------------------------------------------------------------------------
# Date / age helpers
# ---------------------------------------------------------------------------

def calculate_age(dob: date, on_date: Optional[date] = None) -> int:
    on_date = on_date or date.today()
    years = on_date.year - dob.year
    if (on_date.month, on_date.day) < (dob.month, dob.day):
        years -= 1
    return years


def days_until(target: date, from_date: Optional[date] = None) -> int:
    from_date = from_date or date.today()
    return (target - from_date).days


def next_birthday(dob: date, from_date: Optional[date] = None) -> date:
    """Return the next occurrence of the user's birthday on/after from_date."""
    from_date = from_date or date.today()
    this_year_bday = date(from_date.year, dob.month, dob.day)
    if this_year_bday >= from_date:
        return this_year_bday
    return date(from_date.year + 1, dob.month, dob.day)


def weeks_between(start: date, end: date) -> float:
    return max((end - start).days, 0) / 7.0


def months_between(start: date, end: date) -> float:
    return max((end - start).days, 0) / 30.4375


# ---------------------------------------------------------------------------
# Body metrics
# ---------------------------------------------------------------------------

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if not height_cm or height_cm <= 0:
        return 0.0
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float) -> str:
    if bmi <= 0:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Healthy"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def healthy_weight_range_kg(height_cm: float) -> tuple[float, float]:
    """BMI 18.5-24.9 range converted to kg for the given height."""
    height_m = height_cm / 100.0
    low = 18.5 * (height_m ** 2)
    high = 24.9 * (height_m ** 2)
    return round(low, 1), round(high, 1)


# ---------------------------------------------------------------------------
# Weight series helpers
# ---------------------------------------------------------------------------

def get_latest_weight(df: pd.DataFrame, fallback: float) -> float:
    if df is None or df.empty:
        return fallback
    weight_series = df.dropna(subset=["weight_kg"])
    if weight_series.empty:
        return fallback
    weight_series = weight_series.sort_values("log_date")
    return float(weight_series.iloc[-1]["weight_kg"])


def rolling_average(df: pd.DataFrame, column: str, window_days: int) -> pd.DataFrame:
    """Return a date-indexed rolling average series for the given column."""
    if df is None or df.empty or column not in df.columns:
        return pd.DataFrame(columns=["log_date", column])
    series = df.dropna(subset=[column]).sort_values("log_date").copy()
    if series.empty:
        return pd.DataFrame(columns=["log_date", column])
    series = series.set_index("log_date")[column].resample("D").mean()
    rolled = series.rolling(window=window_days, min_periods=1).mean()
    out = rolled.reset_index()
    out.columns = ["log_date", column]
    return out


def weekly_average(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df is None or df.empty or column not in df.columns:
        return pd.DataFrame(columns=["week_start", column])
    series = df.dropna(subset=[column]).sort_values("log_date").copy()
    if series.empty:
        return pd.DataFrame(columns=["week_start", column])
    series = series.set_index("log_date")
    weekly = series[column].resample("W-MON", label="left", closed="left").mean()
    out = weekly.reset_index()
    out.columns = ["week_start", column]
    return out.dropna()


def monthly_average(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df is None or df.empty or column not in df.columns:
        return pd.DataFrame(columns=["month_start", column])
    series = df.dropna(subset=[column]).sort_values("log_date").copy()
    if series.empty:
        return pd.DataFrame(columns=["month_start", column])
    series = series.set_index("log_date")
    monthly = series[column].resample("MS").mean()
    out = monthly.reset_index()
    out.columns = ["month_start", column]
    return out.dropna()


def weight_loss_velocity_kg_per_week(df: pd.DataFrame, lookback_days: int = 14) -> float:
    """
    Compute recent weight-loss velocity (kg/week) using a simple linear
    regression over the most recent `lookback_days` of logged weight.
    Positive value = losing weight; negative = gaining.
    """
    if df is None or df.empty:
        return 0.0
    weight_df = df.dropna(subset=["weight_kg"]).sort_values("log_date")
    if weight_df.empty:
        return 0.0

    cutoff = weight_df["log_date"].max() - timedelta(days=lookback_days)
    recent = weight_df[weight_df["log_date"] >= cutoff]
    if len(recent) < 2:
        return 0.0

    x = (recent["log_date"] - recent["log_date"].min()).dt.days.values.astype(float)
    y = recent["weight_kg"].values.astype(float)

    if np.all(x == x[0]):
        return 0.0

    slope_per_day = np.polyfit(x, y, 1)[0]
    slope_per_week = slope_per_day * 7.0
    # Loss is negative slope; report as positive "velocity of loss"
    return round(-slope_per_week, 2)


# ---------------------------------------------------------------------------
# Smart Goal Engine
# ---------------------------------------------------------------------------

def predict_weight_on_date(
    df: pd.DataFrame,
    current_weight: float,
    target_date: date,
    lookback_days: int = 21,
) -> float:
    """
    Predict weight on a future target_date by projecting the recent
    linear trend (kg/day) forward. Falls back to current_weight if there
    isn't enough data for a trend.
    """
    velocity_per_week = weight_loss_velocity_kg_per_week(df, lookback_days=lookback_days)
    days_ahead = days_until(target_date)
    if days_ahead <= 0:
        return round(current_weight, 1)

    daily_rate = velocity_per_week / 7.0
    predicted = current_weight - (daily_rate * days_ahead)
    return round(predicted, 1)


def required_weekly_loss_kg(current_weight: float, goal_weight: float, target_date: date) -> float:
    weeks_left = weeks_between(date.today(), target_date)
    if weeks_left <= 0:
        return 0.0
    total_to_lose = current_weight - goal_weight
    return round(total_to_lose / weeks_left, 3)


def required_monthly_loss_kg(current_weight: float, goal_weight: float, target_date: date) -> float:
    months_left = months_between(date.today(), target_date)
    if months_left <= 0:
        return 0.0
    total_to_lose = current_weight - goal_weight
    return round(total_to_lose / months_left, 2)


def goal_progress_pct(start_weight: float, current_weight: float, goal_weight: float) -> float:
    total_change_needed = start_weight - goal_weight
    if total_change_needed <= 0:
        return 100.0
    achieved = start_weight - current_weight
    pct = (achieved / total_change_needed) * 100.0
    return round(max(0.0, min(100.0, pct)), 1)


def track_status(
    current_weight: float,
    goal_weight: float,
    start_weight: float,
    start_date: date,
    target_date: date,
) -> str:
    """
    Compare actual progress against the ideal linear path between
    start_date/start_weight and target_date/goal_weight.
    """
    total_days = (target_date - start_date).days
    elapsed_days = (date.today() - start_date).days
    if total_days <= 0 or elapsed_days <= 0:
        return "On Track"

    elapsed_days = min(elapsed_days, total_days)
    expected_progress_fraction = elapsed_days / total_days
    expected_weight = start_weight - (start_weight - goal_weight) * expected_progress_fraction

    diff = current_weight - expected_weight  # positive => heavier than expected => behind

    if diff > 0.7:
        return "Behind"
    elif diff < -0.7:
        return "Ahead"
    else:
        return "On Track"


def dynamic_recommendations(
    status: str,
    velocity: float,
    required_weekly: float,
    steps_avg: Optional[float],
    water_avg: Optional[float],
    protein_avg: Optional[float],
    walking_avg: Optional[float],
) -> list[str]:
    """Generate context-aware, joint-friendly recommendations."""
    recs: list[str] = []

    if status == "Behind":
        gap = round(required_weekly - velocity, 2)
        if gap > 0:
            recs.append(
                f"You're behind pace by about {gap} kg/week. Try adding 10-15 minutes "
                "of extra treadmill or walking-pad time at an easy pace to protect your knees."
            )
        recs.append(
            "Swap one higher-carb meal (e.g., extra rotli/rice) for more dal, kathol, "
            "or paneer to raise protein while keeping calories controlled."
        )
    elif status == "Ahead":
        recs.append(
            "Great pace! Make sure you're still eating enough protein and not losing "
            "weight too fast, which can affect energy and muscle tone."
        )
    else:
        recs.append("You're right on track. Keep your current routine consistent.")

    if steps_avg is not None and steps_avg < STEPS_GOAL_DEFAULT:
        recs.append(
            f"Average steps ({int(steps_avg)}) are below your {STEPS_GOAL_DEFAULT} target. "
            "Short, frequent walking-pad sessions are gentler on knees than long walks."
        )

    if water_avg is not None and water_avg < WATER_GOAL_ML_DEFAULT:
        recs.append(
            f"Water intake is averaging {int(water_avg)} ml - aim closer to "
            f"{int(WATER_GOAL_ML_DEFAULT)} ml/day to support metabolism and reduce water retention."
        )

    if protein_avg is not None and protein_avg < PROTEIN_GOAL_G_DEFAULT:
        recs.append(
            f"Protein is averaging {int(protein_avg)} g/day. As an egg-free vegetarian, "
            f"lean on paneer, dahi/curd, moong dal, chana, soya chunks, and a protein-rich "
            f"snack to reach {int(PROTEIN_GOAL_G_DEFAULT)}g+."
        )

    if walking_avg is not None and walking_avg < WALK_MIN_GOAL_DEFAULT:
        recs.append(
            f"Walking minutes are averaging {int(walking_avg)} - try splitting walks into "
            "2-3 short, knee-friendly sessions on the walking pad or treadmill instead of one long one."
        )

    recs.append(
        "Include 15-20 minutes of gentle yoga (e.g., cat-cow, seated forward bends, "
        "supported chair yoga) most days to support joint mobility without strain."
    )

    return recs


# ---------------------------------------------------------------------------
# Scoring (Reports)
# ---------------------------------------------------------------------------

def consistency_score(df: pd.DataFrame, start: date, end: date) -> float:
    """
    % of days in [start, end] that have at least one logged metric
    (weight, steps, calories, or walking minutes).
    """
    total_days = (end - start).days + 1
    if total_days <= 0:
        return 0.0
    if df is None or df.empty:
        return 0.0

    mask = (df["log_date"] >= pd.Timestamp(start)) & (df["log_date"] <= pd.Timestamp(end))
    window = df.loc[mask]
    if window.empty:
        return 0.0

    has_any = window[["weight_kg", "steps", "calories", "walking_minutes"]].notna().any(axis=1)
    logged_days = has_any.sum()
    return round((logged_days / total_days) * 100.0, 1)


def progress_score(
    weight_change_actual: float,
    weight_change_expected: float,
    consistency: float,
) -> float:
    """
    Composite 0-100 score blending how much weight was actually lost
    vs. expected pace (60% weight) and logging consistency (40% weight).
    """
    if weight_change_expected <= 0:
        weight_component = 100.0
    else:
        ratio = weight_change_actual / weight_change_expected
        weight_component = max(0.0, min(100.0, ratio * 100.0))

    score = (0.6 * weight_component) + (0.4 * consistency)
    return round(max(0.0, min(100.0, score)), 1)


def fat_loss_estimate_kg(calorie_deficit_total: float) -> float:
    """Convert a total calorie deficit into an estimated fat mass loss in kg."""
    if calorie_deficit_total <= 0:
        return 0.0
    return round(calorie_deficit_total / KCAL_PER_KG_FAT, 2)


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#2E5077",
                "font_color": "white",
                "border": 1,
            }
        )
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, max(14, len(str(value)) + 2))
    buffer.seek(0)
    return buffer.getvalue()


def safe_round(value, ndigits=1):
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None
