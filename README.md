# Institution TJ Scholar Dashboard

Streamlit dashboard for JFDs: **Current Status EY25**, **Individual Student Data - EY25**, and **EY 26 Programming**.

## Views

- **Current Status EY25** — First Final Exam outcomes, borderline students, score improvement, test date distribution, Interventions (categories, score distribution, % not passing, intervened vs responded, student list with response and Jun–Dec attendance tier).
- **Individual Student Data - EY25** — Per-student practice exam scores, attendance, completed question sets, accuracy, and completed lessons. Data sections show “Updated through [date]” where applicable.
- **EY 26 Programming** — Schedule flexibility, options (Summer/Fall/Spring), front-load chemistry/physics rationale, June/July comparisons, and calendar PDF. Goal: schedule finalized by end of March for EY26 for instructor headcount.

## Data files (optional)

- `institution-1-engagement-data.csv` — Required for Individual Student Data.
- `institution-1-test-data.csv` — For practice exam scores and Current Status / Interventions.
- `tier.csv` — For attendance tiers and intervention table.
- `Interventions_initial.csv` — For Interventions section.
- `roster.csv` — For student roster (reference) at top of dashboard.

## Surveys & resources

- [Texas JAMP Scholars | MCAT Exam Schedule & Scores Survey](https://docs.google.com/spreadsheets/d/10YBmWD7qFD0fjbD-8TK1gxNMVpwJyTLtOFtT1huh-FI/edit?usp=sharing)

## Run

```bash
pip install -r requirements.txt
streamlit run main.py
```
