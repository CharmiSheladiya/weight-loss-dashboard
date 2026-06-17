# 🌿 Personal Weight Loss Dashboard

A production-quality, mobile-responsive weight loss tracking dashboard built with Streamlit, SQLite, Pandas, and Plotly. Designed for an Indian Gujarati vegetarian (egg-free) diet with a low-impact, knee-friendly exercise routine (walking, treadmill, walking pad, yoga).

## Features

- **Dashboard** — current/goal weight, weight remaining, days until birthday, goal progress %, weekly/monthly averages, predicted birthday weight, target vs actual gauge, loss velocity.
- **Daily Tracker** — log weight, steps, calories, protein, water, walking minutes, and notes. Full history table.
- **Analytics** — weight/weekly/monthly/calories/steps trend charts, goal projection chart.
- **Smart Goal Engine** — predicts weight on target date, required weekly/monthly loss, On Track / Behind / Ahead status, dynamic personalized recommendations.
- **Reports** — weekly/monthly report, fat-loss estimate, consistency score, progress score.
- **Profile & Export** — editable profile, CSV and Excel export.

## Project Structure

```
weight-loss-dashboard/
├── app.py                  # Main Streamlit app (UI + page routing)
├── database.py             # SQLite persistence layer (auto-creates tables)
├── analytics.py            # Plotly chart builders
├── utils.py                # Date math, BMI, Smart Goal Engine, scoring, exports
├── seed_data.py            # Optional: populate demo data
├── requirements.txt
├── .gitignore
├── README.md
├── .streamlit/
│   └── config.toml         # Theme + server config
└── data/
    └── weight_tracker.db   # SQLite database (auto-created on first run)
```

## Run Locally (Mac)

```bash
cd weight-loss-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed_data.py        # optional — adds 60 days of sample data
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Deploy on Streamlit Community Cloud (Free)

1. Push this folder to a new GitHub repository.
2. Go to https://share.streamlit.io → "New app".
3. Select your repo, branch `main`, and main file path `app.py`.
4. Click **Deploy**.

No environment variables or secrets are required for this app — it uses local SQLite storage with no external API keys.

**Note on persistence:** Streamlit Community Cloud's filesystem is ephemeral on redeploys/restarts. For long-term, always-on persistence across redeploys, periodically export via the in-app CSV/Excel download, or swap `database.py`'s connection target to a hosted database (e.g., Turso/LibSQL, Supabase Postgres) later — the rest of the app is unaffected since all DB access goes through `database.py`.

## Tech Stack

Python · Streamlit · SQLite · Pandas · NumPy · Plotly · XlsxWriter
