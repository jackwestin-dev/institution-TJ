# Institution TJ Scholar Dashboard

Streamlit dashboard for JFDs: **Current Status EY25**, **Individual Student Data - EY25**, and **EY 26 Programming**.

## Views

- **Current Status EY25** — First Final Exam outcomes, borderline students, score improvement, test date distribution, Interventions (categories, score distribution, % not passing, intervened vs responded, student list with response and Jun–Dec attendance tier).
- **Individual Student Data - EY25** — Per-student practice exam scores, attendance, completed question sets, accuracy, and completed lessons. Data sections show “Updated through [date]” where applicable.
- **EY 26 Programming** — Schedule flexibility, options (Summer/Fall/Spring), front-load chemistry/physics rationale, June/July comparisons, and calendar PDF. Goal: schedule finalized by end of March for EY26 for instructor headcount.
- **Summer EY25 and EY26** — Side-by-side engagement for the two summer cohorts. Nova session **attendance** (June 2026, tracked as sessions attended ÷ offered) plus Canvas **accuracy** and **participation** per session. Cohort → system IDs: EY26 = Canvas course 345 / Nova class 722; EY25 = Canvas course 351 / Nova class 664.

## Data files (optional)

- `institution-1-engagement-data.csv` — Required for Individual Student Data.
- `institution-1-test-data.csv` — For practice exam scores and Current Status / Interventions.
- `tier.csv` — For attendance tiers and intervention table.
- `Interventions_initial.csv` — For Interventions section.
- `roster.csv` — For student roster (reference) at top of dashboard.
- `summer_canvas_metrics.csv` — Canvas accuracy/participation per session (aggregate) for the Summer EY25/EY26 view.
- `summer_attendance_sample.csv` — Sample Nova attendance in the attendance-tracker skill's output shape; replace with the skill's real June 2026 pull.

## Surveys & resources

- [Texas JAMP Scholars | MCAT Exam Schedule & Scores Survey](https://docs.google.com/spreadsheets/d/10YBmWD7qFD0fjbD-8TK1gxNMVpwJyTLtOFtT1huh-FI/edit?usp=sharing)

## Run

```bash
pip install -r requirements.txt
streamlit run main.py
```
