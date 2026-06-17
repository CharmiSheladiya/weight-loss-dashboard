"""
app.py
Personal Weight Loss Dashboard — main Streamlit entry point.

Run locally with:
    streamlit run app.py

Pages:
    Dashboard | Daily Tracker | Analytics | Smart Goal Engine | Reports | Profile & Export
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

import analytics
import database as db
import utils

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Weight Loss Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — modern, professional, mobile-responsive theme
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Hide default Streamlit chrome for a cleaner look */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent;}

/* App background */
.stApp {
    background: linear-gradient(180deg, #F7F9FC 0%, #EFF3F8 100%);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B3A57 0%, #2E5077 100%);
}
section[data-testid="stSidebar"] * {
    color: #F1F5F9 !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.95rem;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15);
}

/* KPI Card */
.kpi-card {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 2px 10px rgba(16, 30, 54, 0.06);
    border: 1px solid #EDF1F7;
    height: 100%;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(16, 30, 54, 0.10);
}
.kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 1.65rem;
    font-weight: 800;
    color: #1B2A41;
    line-height: 1.15;
}
.kpi-sub {
    font-size: 0.8rem;
    font-weight: 500;
    margin-top: 4px;
}
.kpi-sub.positive { color: #2F9461; }
.kpi-sub.negative { color: #D9534F; }
.kpi-sub.neutral { color: #9AA5B1; }

/* Status badge */
.status-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.02em;
}
.status-ontrack { background: #E5F3EC; color: #1F8A53; }
.status-behind { background: #FBEAEA; color: #C0392B; }
.status-ahead { background: #EDE7FA; color: #6C3FC5; }

/* Section header */
.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1B2A41;
    margin-top: 6px;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 2px solid #E5EAF1;
}

/* Recommendation card */
.rec-card {
    background: #FFFFFF;
    border-left: 4px solid #4FB286;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 0.92rem;
    color: #374151;
    box-shadow: 0 1px 4px rgba(16,30,54,0.05);
}

/* Buttons */
.stButton button, .stDownloadButton button {
    border-radius: 10px;
    font-weight: 600;
    border: none;
    padding: 0.55rem 1.2rem;
}
.stButton button[kind="primary"], .stDownloadButton button {
    background: linear-gradient(135deg, #2E5077, #4FB286);
    color: white;
}

/* Metric containers from st.metric */
div[data-testid="stMetricValue"] {
    font-weight: 800;
    color: #1B2A41;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
    .kpi-value { font-size: 1.35rem; }
    .section-title { font-size: 1.05rem; }
}

/* Dataframe container rounding */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Initialize database
# ---------------------------------------------------------------------------

db.init_db()


# ---------------------------------------------------------------------------
# Cached data loaders (cleared on every write so UI always reflects latest)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=5, show_spinner=False)
def load_logs() -> pd.DataFrame:
    return db.get_all_logs_df()


@st.cache_data(ttl=5, show_spinner=False)
def load_profile() -> dict:
    return db.get_profile()


def refresh_data():
    load_logs.clear()
    load_profile.clear()


# ---------------------------------------------------------------------------
# KPI card helper
# ---------------------------------------------------------------------------

def kpi_card(label: str, value: str, sub: str = "", sub_class: str = "neutral"):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub {sub_class}">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge_html(status: str) -> str:
    css_class = {
        "On Track": "status-ontrack",
        "Behind": "status-behind",
        "Ahead": "status-ahead",
    }.get(status, "status-ontrack")
    icon = {"On Track": "✅", "Behind": "⚠️", "Ahead": "🚀"}.get(status, "✅")
    return f'<span class="status-badge {css_class}">{icon} {status}</span>'


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 10px 0 20px 0;">
            <div style="font-size: 2.2rem;">🌿</div>
            <div style="font-size: 1.25rem; font-weight: 800; color:white;">Weight Loss Dashboard</div>
            <div style="font-size: 0.8rem; color:#C9D6E3; margin-top:4px;">Personal Health Tracker</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏠 Dashboard",
            "📝 Daily Tracker",
            "📊 Analytics",
            "🎯 Smart Goal Engine",
            "📄 Reports",
            "⚙️ Profile & Export",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    profile = load_profile()
    if profile:
        st.markdown(
            f"""
            <div style="font-size:0.82rem; color:#C9D6E3; line-height:1.6;">
                <b>{profile.get('name', 'My Profile')}</b><br>
                Height: {profile.get('height_cm', 0):.0f} cm<br>
                Goal: {profile.get('goal_weight_kg', 0):.1f} kg by<br>
                {profile.get('target_date', '')}
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("---")
    st.caption("Diet focus: Gujarati vegetarian, egg-free")
    st.caption("Exercise: Walking · Treadmill · Walking pad · Yoga")
    st.caption("Built with Streamlit · SQLite · Plotly")


# ---------------------------------------------------------------------------
# Shared computed context (used across multiple pages)
# ---------------------------------------------------------------------------

profile = load_profile()
logs_df = load_logs()

dob = datetime.strptime(profile["dob"], "%Y-%m-%d").date()
height_cm = float(profile["height_cm"])
start_weight = float(profile["start_weight_kg"])
goal_weight = float(profile["goal_weight_kg"])
target_date = datetime.strptime(profile["target_date"], "%Y-%m-%d").date()

# Determine "start date" as the earliest log date, else 90 days ago as a sane default
if not logs_df.empty and not logs_df["weight_kg"].dropna().empty:
    start_date_for_status = logs_df.dropna(subset=["weight_kg"]).sort_values("log_date").iloc[0]["log_date"].date()
else:
    start_date_for_status = date.today() - timedelta(days=1)

current_weight = utils.get_latest_weight(logs_df, fallback=start_weight)
weight_remaining = round(current_weight - goal_weight, 1)
goal_pct = utils.goal_progress_pct(start_weight, current_weight, goal_weight)
velocity = utils.weight_loss_velocity_kg_per_week(logs_df)
predicted_bday_weight = utils.predict_weight_on_date(logs_df, current_weight, target_date)
weekly_required = utils.required_weekly_loss_kg(current_weight, goal_weight, target_date)
monthly_required = utils.required_monthly_loss_kg(current_weight, goal_weight, target_date)
status = utils.track_status(current_weight, goal_weight, start_weight, start_date_for_status, target_date)
days_to_target = utils.days_until(target_date)
age_years = utils.calculate_age(dob)
bmi = utils.calculate_bmi(current_weight, height_cm)
bmi_cat = utils.bmi_category(bmi)


# ===========================================================================
# PAGE: DASHBOARD
# ===========================================================================

if page == "🏠 Dashboard":
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
            <div>
                <div style="font-size:1.8rem; font-weight:800; color:#1B2A41;">Welcome back 👋</div>
                <div style="color:#6B7280; font-size:0.95rem;">Here's your progress toward {goal_weight:.0f} kg by {target_date.strftime('%B %d, %Y')}</div>
            </div>
            <div>{status_badge_html(status)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Row 1: Primary KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Current Weight", f"{current_weight:.1f} kg", f"BMI {bmi} · {bmi_cat}", "neutral")
    with c2:
        kpi_card("Goal Weight", f"{goal_weight:.1f} kg", f"by {target_date.strftime('%d %b %Y')}", "neutral")
    with c3:
        sub_cls = "positive" if weight_remaining <= 0 else "negative"
        kpi_card("Weight Remaining", f"{max(weight_remaining,0):.1f} kg", "to reach goal" if weight_remaining > 0 else "Goal achieved! 🎉", sub_cls)
    with c4:
        bday = utils.next_birthday(dob)
        days_bday = utils.days_until(bday)
        kpi_card("Days Until Birthday", f"{days_bday}", f"Turns {age_years + 1} on {bday.strftime('%d %b %Y')}", "neutral")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Row 2: Progress KPIs ---
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        kpi_card("Goal Progress", f"{goal_pct:.1f}%", "of total journey complete", "positive" if goal_pct > 0 else "neutral")
    with c6:
        weekly_avg_w = utils.weekly_average(logs_df, "weight_kg")
        wavg_display = f"{weekly_avg_w.iloc[-1]['weight_kg']:.1f} kg" if not weekly_avg_w.empty else "—"
        kpi_card("Weekly Avg Weight", wavg_display, "last 7-day window", "neutral")
    with c7:
        monthly_avg_w = utils.monthly_average(logs_df, "weight_kg")
        mavg_display = f"{monthly_avg_w.iloc[-1]['weight_kg']:.1f} kg" if not monthly_avg_w.empty else "—"
        kpi_card("Monthly Avg Weight", mavg_display, "last 30-day window", "neutral")
    with c8:
        sub_cls = "positive" if velocity > 0 else ("negative" if velocity < 0 else "neutral")
        kpi_card("Loss Velocity", f"{velocity:+.2f} kg/wk", "based on recent trend", sub_cls)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Row 3: Predicted weight + projection chart ---
    colA, colB = st.columns([1, 2])
    with colA:
        st.markdown('<div class="section-title">Predicted Birthday Weight</div>', unsafe_allow_html=True)
        diff_to_goal = round(predicted_bday_weight - goal_weight, 1)
        sub_cls = "positive" if diff_to_goal <= 0 else "negative"
        sub_text = "On pace to meet goal! 🎉" if diff_to_goal <= 0 else f"{diff_to_goal} kg above goal at current pace"
        kpi_card("Predicted on Target Date", f"{predicted_bday_weight:.1f} kg", sub_text, sub_cls)
        st.markdown("<br>", unsafe_allow_html=True)

        expected_today = start_weight - (start_weight - goal_weight) * (
            (date.today() - start_date_for_status).days / max((target_date - start_date_for_status).days, 1)
        )
        expected_today = max(min(expected_today, start_weight), goal_weight)
        gauge_fig = analytics.target_vs_actual_gauge(current_weight, round(expected_today, 1), goal_weight)
        st.plotly_chart(gauge_fig, use_container_width=True, config={"displayModeBar": False})

    with colB:
        st.markdown('<div class="section-title">Goal Projection</div>', unsafe_allow_html=True)
        proj_fig = analytics.goal_projection_chart(
            logs_df, start_weight, start_date_for_status, goal_weight, target_date, predicted_bday_weight
        )
        st.plotly_chart(proj_fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Weight Trend</div>', unsafe_allow_html=True)
    st.plotly_chart(analytics.weight_trend_chart(logs_df, goal_weight), use_container_width=True, config={"displayModeBar": False})


# ===========================================================================
# PAGE: DAILY TRACKER
# ===========================================================================

elif page == "📝 Daily Tracker":
    st.markdown('<div class="section-title">Daily Tracker</div>', unsafe_allow_html=True)

    tab_entry, tab_history = st.tabs(["➕ Log Entry", "🗂️ History"])

    with tab_entry:
        selected_date = st.date_input("Date", value=date.today(), max_value=date.today())
        existing = db.get_log_for_date(selected_date)

        def existing_val(field, default=None):
            if existing is not None and existing[field] is not None:
                return existing[field]
            return default

        with st.form("daily_log_form", clear_on_submit=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                weight_val = st.number_input(
                    "Weight (kg)", min_value=0.0, max_value=300.0, step=0.1,
                    value=float(existing_val("weight_kg", 0.0) or 0.0), format="%.1f",
                )
                steps_val = st.number_input(
                    "Steps", min_value=0, max_value=100000, step=100,
                    value=int(existing_val("steps", 0) or 0),
                )
            with col2:
                calories_val = st.number_input(
                    "Calories (kcal)", min_value=0.0, max_value=10000.0, step=10.0,
                    value=float(existing_val("calories", 0.0) or 0.0),
                )
                protein_val = st.number_input(
                    "Protein (g)", min_value=0.0, max_value=500.0, step=1.0,
                    value=float(existing_val("protein_g", 0.0) or 0.0),
                )
            with col3:
                water_val = st.number_input(
                    "Water Intake (ml)", min_value=0.0, max_value=10000.0, step=100.0,
                    value=float(existing_val("water_ml", 0.0) or 0.0),
                )
                walking_val = st.number_input(
                    "Walking Minutes", min_value=0.0, max_value=600.0, step=5.0,
                    value=float(existing_val("walking_minutes", 0.0) or 0.0),
                )

            notes_val = st.text_area(
                "Notes (meals, yoga, energy levels, etc.)",
                value=existing_val("notes", "") or "",
                placeholder="e.g., Tea with 240ml non-fat milk + monk fruit, dhokla breakfast, 20 min yoga...",
                height=90,
            )

            submitted = st.form_submit_button("💾 Save Entry", use_container_width=True, type="primary")

            if submitted:
                db.upsert_daily_log(
                    log_date=selected_date,
                    weight_kg=weight_val if weight_val > 0 else None,
                    steps=int(steps_val) if steps_val > 0 else None,
                    calories=calories_val if calories_val > 0 else None,
                    protein_g=protein_val if protein_val > 0 else None,
                    water_ml=water_val if water_val > 0 else None,
                    walking_minutes=walking_val if walking_val > 0 else None,
                    notes=notes_val if notes_val.strip() else None,
                )
                refresh_data()
                st.success(f"Entry saved for {selected_date.strftime('%d %b %Y')} ✅")
                st.rerun()

        if existing is not None:
            if st.button("🗑️ Delete this day's entry", type="secondary"):
                db.delete_daily_log(selected_date)
                refresh_data()
                st.success("Entry deleted.")
                st.rerun()

    with tab_history:
        logs_df_fresh = load_logs()
        if logs_df_fresh.empty:
            st.info("No entries logged yet. Add your first entry in the 'Log Entry' tab.")
        else:
            display_df = logs_df_fresh.sort_values("log_date", ascending=False).copy()
            display_df["log_date"] = display_df["log_date"].dt.strftime("%Y-%m-%d")
            display_df = display_df[
                ["log_date", "weight_kg", "steps", "calories", "protein_g", "water_ml", "walking_minutes", "notes"]
            ]
            display_df.columns = [
                "Date", "Weight (kg)", "Steps", "Calories", "Protein (g)", "Water (ml)", "Walking (min)", "Notes"
            ]
            st.dataframe(display_df, use_container_width=True, height=480, hide_index=True)


# ===========================================================================
# PAGE: ANALYTICS
# ===========================================================================

elif page == "📊 Analytics":
    st.markdown('<div class="section-title">Analytics</div>', unsafe_allow_html=True)

    if logs_df.empty:
        st.info("Log a few days of data in Daily Tracker to unlock analytics charts.")
    else:
        st.plotly_chart(analytics.weight_trend_chart(logs_df, goal_weight), use_container_width=True, config={"displayModeBar": False})

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                analytics.weekly_trend_chart(logs_df, "weight_kg", "Weight (kg)", analytics.COLOR_PRIMARY),
                use_container_width=True, config={"displayModeBar": False},
            )
        with col2:
            st.plotly_chart(
                analytics.monthly_trend_chart(logs_df, "weight_kg", "Weight (kg)", analytics.COLOR_GOAL),
                use_container_width=True, config={"displayModeBar": False},
            )

        st.plotly_chart(analytics.calories_trend_chart(logs_df), use_container_width=True, config={"displayModeBar": False})
        st.plotly_chart(analytics.steps_trend_chart(logs_df), use_container_width=True, config={"displayModeBar": False})

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(
                analytics.weekly_trend_chart(logs_df, "steps", "Steps", analytics.COLOR_ACCENT),
                use_container_width=True, config={"displayModeBar": False},
            )
        with col4:
            st.plotly_chart(
                analytics.weekly_trend_chart(logs_df, "calories", "Calories", analytics.COLOR_WARNING),
                use_container_width=True, config={"displayModeBar": False},
            )

        st.markdown('<div class="section-title">Goal Projection</div>', unsafe_allow_html=True)
        st.plotly_chart(
            analytics.goal_projection_chart(
                logs_df, start_weight, start_date_for_status, goal_weight, target_date, predicted_bday_weight
            ),
            use_container_width=True, config={"displayModeBar": False},
        )


# ===========================================================================
# PAGE: SMART GOAL ENGINE
# ===========================================================================

elif page == "🎯 Smart Goal Engine":
    st.markdown('<div class="section-title">Smart Goal Engine</div>', unsafe_allow_html=True)
    st.markdown(status_badge_html(status), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Predicted Weight on Target Date", f"{predicted_bday_weight:.1f} kg", target_date.strftime("%d %b %Y"))
    with c2:
        kpi_card("Required Weekly Loss", f"{weekly_required:.3f} kg/wk", "to reach goal on time")
    with c3:
        kpi_card("Required Monthly Loss", f"{monthly_required:.2f} kg/mo", "to reach goal on time")

    st.markdown("<br>", unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        kpi_card("Current Pace", f"{velocity:+.2f} kg/wk", "based on last 14 days")
    with c5:
        kpi_card("Days Remaining", f"{days_to_target}", f"until {target_date.strftime('%d %b %Y')}")
    with c6:
        kpi_card("Total To Lose", f"{max(current_weight - goal_weight, 0):.1f} kg", "from current weight")

    st.markdown("<br>", unsafe_allow_html=True)
    st.plotly_chart(
        analytics.goal_projection_chart(
            logs_df, start_weight, start_date_for_status, goal_weight, target_date, predicted_bday_weight
        ),
        use_container_width=True, config={"displayModeBar": False},
    )

    st.markdown('<div class="section-title">Dynamic Recommendations</div>', unsafe_allow_html=True)

    recent_30 = utils.weeks_between(date.today() - timedelta(days=30), date.today())
    window_df = logs_df[logs_df["log_date"] >= pd.Timestamp(date.today() - timedelta(days=30))] if not logs_df.empty else logs_df
    steps_avg = window_df["steps"].dropna().mean() if not window_df.empty and window_df["steps"].notna().any() else None
    water_avg = window_df["water_ml"].dropna().mean() if not window_df.empty and window_df["water_ml"].notna().any() else None
    protein_avg = window_df["protein_g"].dropna().mean() if not window_df.empty and window_df["protein_g"].notna().any() else None
    walking_avg = window_df["walking_minutes"].dropna().mean() if not window_df.empty and window_df["walking_minutes"].notna().any() else None

    recs = utils.dynamic_recommendations(
        status, velocity, weekly_required, steps_avg, water_avg, protein_avg, walking_avg
    )
    for r in recs:
        st.markdown(f'<div class="rec-card">💡 {r}</div>', unsafe_allow_html=True)


# ===========================================================================
# PAGE: REPORTS
# ===========================================================================

elif page == "📄 Reports":
    st.markdown('<div class="section-title">Reports</div>', unsafe_allow_html=True)

    report_type = st.radio("Report Period", ["Weekly", "Monthly"], horizontal=True)

    today = date.today()
    if report_type == "Weekly":
        period_start = today - timedelta(days=6)
    else:
        period_start = today - timedelta(days=29)
    period_end = today

    window = utils.weeks_between(period_start, period_end)
    window_df = logs_df[
        (logs_df["log_date"] >= pd.Timestamp(period_start)) & (logs_df["log_date"] <= pd.Timestamp(period_end))
    ] if not logs_df.empty else logs_df

    st.caption(f"Reporting period: {period_start.strftime('%d %b %Y')} → {period_end.strftime('%d %b %Y')}")

    weight_logged = window_df.dropna(subset=["weight_kg"]).sort_values("log_date") if not window_df.empty else window_df
    if not weight_logged.empty and len(weight_logged) >= 2:
        weight_change_actual = round(weight_logged.iloc[0]["weight_kg"] - weight_logged.iloc[-1]["weight_kg"], 2)
    else:
        weight_change_actual = 0.0

    expected_loss = (weekly_required * window) if report_type == "Weekly" else monthly_required * (window / 4.345)
    if report_type == "Weekly":
        expected_loss = weekly_required
    else:
        expected_loss = monthly_required

    consistency = utils.consistency_score(logs_df, period_start, period_end)
    prog_score = utils.progress_score(weight_change_actual, max(expected_loss, 0.01), consistency)

    avg_calories = window_df["calories"].dropna().mean() if not window_df.empty and window_df["calories"].notna().any() else 0
    bmr_estimate = 655 + (9.6 * current_weight) + (1.8 * height_cm) - (4.7 * age_years)  # Mifflin/Harris female estimate
    activity_factor = 1.3  # light activity, joint-conscious routine
    tdee_estimate = bmr_estimate * activity_factor
    days_in_window = max((period_end - period_start).days + 1, 1)
    total_deficit = (tdee_estimate - avg_calories) * days_in_window if avg_calories > 0 else 0
    fat_loss_est = utils.fat_loss_estimate_kg(total_deficit)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sub_cls = "positive" if weight_change_actual > 0 else "neutral"
        kpi_card("Weight Change", f"{weight_change_actual:+.2f} kg", "lost in period" if weight_change_actual > 0 else "no net change", sub_cls)
    with c2:
        kpi_card("Fat-Loss Estimate", f"{fat_loss_est:.2f} kg", "from calorie deficit (est.)", "neutral")
    with c3:
        kpi_card("Consistency Score", f"{consistency:.0f}%", "days logged in period", "positive" if consistency >= 70 else "negative")
    with c4:
        kpi_card("Progress Score", f"{prog_score:.0f}/100", "pace + consistency blend", "positive" if prog_score >= 60 else "negative")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Metrics Overview</div>', unsafe_allow_html=True)
    st.plotly_chart(analytics.metrics_overview_chart(window_df), use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-title">Daily Goal Tracking</div>', unsafe_allow_html=True)
    d1, d2, d3 = st.columns(3)
    latest_water = window_df["water_ml"].dropna().iloc[-1] if not window_df.empty and window_df["water_ml"].notna().any() else 0
    latest_protein = window_df["protein_g"].dropna().iloc[-1] if not window_df.empty and window_df["protein_g"].notna().any() else 0
    latest_steps = window_df["steps"].dropna().iloc[-1] if not window_df.empty and window_df["steps"].notna().any() else 0
    with d1:
        st.plotly_chart(
            analytics.daily_goal_donut(latest_water, utils.WATER_GOAL_ML_DEFAULT, "Water Intake", "ml", analytics.COLOR_PRIMARY),
            use_container_width=True, config={"displayModeBar": False},
        )
    with d2:
        st.plotly_chart(
            analytics.daily_goal_donut(latest_protein, utils.PROTEIN_GOAL_G_DEFAULT, "Protein", "g", analytics.COLOR_ACCENT),
            use_container_width=True, config={"displayModeBar": False},
        )
    with d3:
        st.plotly_chart(
            analytics.daily_goal_donut(latest_steps, utils.STEPS_GOAL_DEFAULT, "Steps", "steps", analytics.COLOR_WARNING),
            use_container_width=True, config={"displayModeBar": False},
        )

    st.markdown('<div class="section-title">Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="rec-card">
        📋 During this {report_type.lower()} period, you logged data on {consistency:.0f}% of days and
        {"lost " + str(weight_change_actual) + " kg" if weight_change_actual > 0 else "maintained your weight"}.
        Your estimated fat-loss from calorie tracking is {fat_loss_est:.2f} kg. Current status:
        <b>{status}</b> relative to your {goal_weight:.0f} kg goal by {target_date.strftime('%d %b %Y')}.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE: PROFILE & EXPORT
# ===========================================================================

elif page == "⚙️ Profile & Export":
    st.markdown('<div class="section-title">Profile Settings</div>', unsafe_allow_html=True)

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name_in = st.text_input("Name", value=profile.get("name", "My Profile"))
            gender_in = st.selectbox("Gender", ["Female", "Male", "Other"], index=["Female", "Male", "Other"].index(profile.get("gender", "Female")))
            dob_in = st.date_input("Date of Birth", value=dob, min_value=date(1930, 1, 1), max_value=date.today())
            height_in = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=height_cm, step=0.5)
        with col2:
            start_weight_in = st.number_input("Start Weight (kg)", min_value=20.0, max_value=300.0, value=start_weight, step=0.1)
            goal_weight_in = st.number_input("Goal Weight (kg)", min_value=20.0, max_value=300.0, value=goal_weight, step=0.1)
            target_date_in = st.date_input("Target Date", value=target_date, min_value=date.today())

        save_profile = st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True)
        if save_profile:
            db.update_profile(
                name=name_in, gender=gender_in, dob=dob_in, height_cm=height_in,
                start_weight_kg=start_weight_in, goal_weight_kg=goal_weight_in, target_date=target_date_in,
            )
            refresh_data()
            st.success("Profile updated ✅")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Diet & Exercise Preferences</div>', unsafe_allow_html=True)
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        st.markdown(
            """
            <div class="rec-card">
            🍵 <b>Diet:</b> Indian Gujarati vegetarian, no eggs<br>
            ☕ Tea with 240 ml non-fat milk + monk fruit<br>
            🍳 Savory breakfast<br>
            🍽️ One large dinner<br>
            🥗 One snack
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pcol2:
        st.markdown(
            """
            <div class="rec-card">
            🚶 <b>Exercise:</b> Walking, Treadmill, Walking Pad, Yoga<br>
            🦵 Mild knee pain — low-impact routine prioritized<br>
            🎯 Steps target: 7,000/day (knee-friendly)<br>
            ⏱️ Walking target: 30 min/day (split sessions OK)
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Export Data</div>', unsafe_allow_html=True)

    if logs_df.empty:
        st.info("No data to export yet. Add entries in Daily Tracker first.")
    else:
        export_df = logs_df.copy()
        export_df["log_date"] = export_df["log_date"].dt.strftime("%Y-%m-%d")
        export_df = export_df[
            ["log_date", "weight_kg", "steps", "calories", "protein_g", "water_ml", "walking_minutes", "notes"]
        ]
        export_df.columns = [
            "Date", "Weight (kg)", "Steps", "Calories", "Protein (g)", "Water (ml)", "Walking (min)", "Notes"
        ]

        ecol1, ecol2 = st.columns(2)
        with ecol1:
            st.download_button(
                "⬇️ Download as CSV",
                data=utils.df_to_csv_bytes(export_df),
                file_name=f"weight_tracker_export_{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with ecol2:
            st.download_button(
                "⬇️ Download as Excel",
                data=utils.df_to_excel_bytes(export_df, sheet_name="Weight Tracker"),
                file_name=f"weight_tracker_export_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Database location: {db.get_db_path()}")
