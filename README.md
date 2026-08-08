# Institution TJ Scholar Dashboard

Streamlit dashboard for JFDs. The sidebar has two sections, each with its own radio:

- **Scholar Dashboard** — the cohort views, all driven by static CSVs in this repo.
- **Canvas Accuracy** — Canvas New Quizzes reporting, MCAT exam growth, and Nova attendance, all live against the Canvas and Nova APIs.

## Scholar Dashboard views

- **Current Status EY25** — First Final Exam outcomes, borderline students, score improvement, test date distribution, Interventions (categories, score distribution, % not passing, intervened vs responded, student list with response and Jun–Dec attendance tier).
- **Individual Student Data - EY25** — Per-student practice exam scores, attendance, completed question sets, accuracy, and completed lessons. Data sections show “Updated through [date]” where applicable.
- **EY 26 Programming** — Schedule flexibility, options (Summer/Fall/Spring), front-load chemistry/physics rationale, June/July comparisons, and calendar PDF. Goal: schedule finalized by end of March for EY26 for instructor headcount.
- **Summer EY25 and EY26** — Side-by-side engagement for the two summer cohorts. Nova session **attendance** (June 2026, tracked as sessions attended ÷ offered) plus Canvas **accuracy** and **participation** per session. Cohort → system IDs: EY26 = Canvas course 345 / Nova class 722; EY25 = Canvas course 351 / Nova class 664.

## Canvas Accuracy views

- **Quiz Reports** — Per-quiz scores, question analysis, cross-quiz comparison, essay review, trends, and module comparison for a Canvas course. Needs a Canvas URL and API token (sidebar, or `st.secrets`).
- **Exam Growth** — MCAT exam 1 → exam 2 growth for the EY26 cohort: score bands, band movement, and participation-vs-improvement correlation.
- **Nova Attendance** — Session attendance for a Nova class. Needs browser cookies pasted into the sidebar; they expire with your browser session.

## Data files (optional)

- `institution-1-engagement-data.csv` — Required for Individual Student Data.
- `institution-1-test-data.csv` — For practice exam scores and Current Status / Interventions.
- `tier.csv` — For attendance tiers and intervention table.
- `Interventions_initial.csv` — For Interventions section.
- `roster.csv` — For student roster (reference) at top of dashboard.
- `data/canvas_metrics.csv` — Canvas accuracy/participation per assignment, built from the report cache by `build_canvas_metrics.py`. Counts only, no names. Powers the Summer EY25/EY26 view.
- `summer_canvas_metrics.csv` — The older hand-built snapshot the above replaces. Kept only as a fallback for checkouts that haven't rebuilt yet.
- `data/attendance.csv` — Real Nova session attendance, per-session counts only. Published from **JAMP EY26 → Attendance → Refresh from Nova → Publish this as a snapshot**. Small-group sessions carry no roster, because only part of the cohort is expected and the export doesn't record which group met.

## Student data never leaves your machine

Two directories are gitignored and must stay that way:

- `reports_cache/` — Canvas "Student Analysis" exports: full names plus every per-question answer.
- `exam_data/` — MCAT score exports, also named.

The deployed app reads `data/canvas_metrics.csv` instead, which is counts only. Committing either directory would put student names in git history permanently, and no later commit can remove them.

## Refreshing Canvas data

Report download drives a headless Chromium through Playwright. Streamlit Community Cloud can't install that binary, and its filesystem is wiped on restart, so syncing is a local step:

```bash
pip install -r requirements.txt -r requirements-dev.txt
playwright install chromium

python sync_reports.py            # fills reports_cache/ (gitignored)
python build_canvas_metrics.py    # reduces it to data/canvas_metrics.csv

git add data/canvas_metrics.csv
git commit -m "Refresh Canvas metrics"
git push
```

`sync_reports.py --help` covers per-course sync, `--force` re-download, and worker count.

## Deploying to Streamlit Community Cloud

Entrypoint is `main.py`. Set these under **Settings → Secrets** (see `.streamlit/secrets.toml.example`):

```toml
password = "..."          # omit this and the dashboard opens with NO password
CANVAS_URL = "https://texasjamp.instructure.com"
CANVAS_TOKEN = "..."
```

`CANVAS_URL` / `CANVAS_TOKEN` just prefill the Quiz Reports sidebar — leave them out and viewers type their own token instead.

## Surveys & resources

- [Texas JAMP Scholars | MCAT Exam Schedule & Scores Survey](https://docs.google.com/spreadsheets/d/10YBmWD7qFD0fjbD-8TK1gxNMVpwJyTLtOFtT1huh-FI/edit?usp=sharing)

## Run

```bash
pip install -r requirements.txt
streamlit run main.py
```

Add `-r requirements-dev.txt` if you also need to refresh Canvas report data locally.
