# Interventions Report — Suggestions & Pre-Deployment Checklist

## 1. Who are “students we’ve intervened with”?

From **Interventions_initial.csv** you have three intervention groups:

- **Group A:** Students with **no reported practice exam scores** (intervention = get them to report scores).
- **Group B:** Students with **no anticipated exam date** (intervention = get them to report a date).
- **Group C:** **Tier 3 students** (495–500 or Tier 3 attendance with First Attempt <502) (intervention = engagement / support).

You can define “intervened” as: anyone who appears in at least one of these lists (by **Student ID**), then join to **institution-1-test-data.csv** and **tier.csv** for trends and engagement.

---

## 2. What to show in a “general report” for intervened students

### 2.1 Score trends

- **Per student:** For each intervened student with at least one valid score in the test data, show:
  - **Lowest → First Attempt → Highest** (or timeline of all reported scores by date).
- **Visual:** Small line or bar chart per student (or a faceted “sparkline” view): x = exam order or date, y = actual exam score.
- **Summary:** Among intervened students who have any reported scores:
  - % who **improved** (highest − lowest > 0).
  - **Average improvement** (points) and **distribution** (e.g. histogram of improvement).
- **Comparison (optional):** Intervened vs non‑intervened: average # of exams reported, average improvement, % passed (First Attempt ≥502).

### 2.2 How many tests they’ve reported

- **Metric:** For each intervened student, count rows in **institution-1-test-data.csv** where **actual_exam_score** is valid (actual MCAT score), as you did elsewhere — “reported exam scores” = count of rows with a real score, not just attempts.
- **Report:**
  - Table: Student ID, intervention group(s), **# reported exam scores**, First Attempt score (if any), Passed (Y/N).
  - Summary: **Distribution of # reported scores** among intervened students (e.g. 0, 1, 2, 3–5, 6+).
  - Highlight: % with **0 or 1** reported scores (struggling to report) vs % with **3+** (more engaged).

### 2.3 Showing they “struggle generally” and need engagement for higher scores

- **Struggle signals (already in your data):**
  - **Low or no reported scores** (0–2) → hard to track progress.
  - **First Attempt <502** (failing) or **495–501** (borderline).
  - **Tier 3** in exam count or attendance (tier.csv) → low engagement.
- **Ways to show it in the report:**
  1. **One summary sentence + one table:**  
     “Among intervened students, X% have fewer than 2 reported exam scores; Y% have First Attempt <502; Z% are Tier 3 in at least one category.”  
     Table: student_id, # reported scores, First Attempt, exam_tier, attendance tiers, “Any Tier 3?”.
  2. **Small charts:**
     - Bar: % of intervened students with 0, 1, 2, 3+ reported scores.
     - Bar: % Passed / Borderline / Failing / No score among intervened.
     - Bar: % with Tier 3 (exam or attendance) vs Tier 1/2.
  3. **Message to reinforce:**  
     “Students with more reported scores and Tier 1/2 engagement have higher pass rates; intervened students with few scores and Tier 3 need more outreach.”

---

## 3. Things to analyze before deployment

Use this as a checklist before you build or ship the report.

### Data & definitions

- [ ] **Intervention list:** Confirm whether “intervened” = anyone in Interventions_initial.csv (any of the 3 groups), or only specific groups (e.g. only Tier 3, or only “no anticipated date”).
- [ ] **Student ID match:** Check that **Student ID** in Interventions_initial.csv matches **student_id** in institution-1-test-data.csv and tier.csv (no duplicates, same type).
- [ ] **Reported exam scores:** Confirm definition (e.g. “rows with valid actual_exam_score in test data”) and that it’s consistent with the rest of the app.
- [ ] **First Attempt / Passed:** Same rule as elsewhere (First Attempt row, score ≥502 = Passed).

### Coverage & quality

- [ ] **Overlap:** How many students appear in more than one intervention group? (Report or footnote.)
- [ ] **Missing in test data:** How many intervened students have **zero** rows in institution-1-test-data? (Report as “no test data”.)
- [ ] **Missing in tier data:** How many intervened students have no tier.csv row? (Decide: exclude from tier stats or show “No tier data”.)

### Metrics to validate

- [ ] **Score trends:** For students with 2+ reported scores, spot-check a few: lowest → First Attempt → highest match the test data.
- [ ] **Counts:** Sum of “# reported exam scores” across intervened students matches (or is explainable vs) total rows in test data for those IDs.
- [ ] **Tier 3:** Count of “Tier 3 in any category” among intervened matches a quick manual check from tier.csv.

### Narrative & audience

- [ ] **Main message:** One sentence you want the report to support (e.g. “Intervened students often have few reported scores and Tier 3 engagement; more engagement is associated with more reported scores and higher pass rates.”).
- [ ] **Audience:** Internal only vs external; drive wording and how strongly you state “struggle” and “need engagement.”

### Technical before deployment

- [ ] **Interventions_initial.csv:** Load and parse correctly (multiple sections, possible empty cells, “TRUE”/“FALSE”).
- [ ] **Performance:** If you have 100+ intervened students and many charts, consider summary-first (tables + 1–2 key charts) and details in expanders or a second page.
- [ ] **Filters:** Decide if report is “all intervened” only or if users can filter by intervention group (No scores / No date / Tier 3).

---

## 4. Suggested report structure (when you build it)

1. **Header:** “Intervention students — summary”
2. **Summary metrics (cards or table):**
   - Total intervened students (and by group if useful).
   - % with at least one reported exam score; % with 3+ reported scores.
   - % Passed (First Attempt ≥502); % Borderline; % Failing; % No First Attempt.
   - % with Tier 3 in any category (exam or attendance).
3. **Score trends:**  
   Short summary (e.g. “X of Y students with 2+ scores improved; average +Z points”) + optional small trend chart or table (lowest / First Attempt / highest per student).
4. **How many tests reported:**  
   Table: student_id, intervention group(s), # reported exam scores, First Attempt, Passed.  
   Optional: bar chart of distribution of # reported scores (0, 1, 2, 3–5, 6+).
5. **Struggle / engagement:**  
   One paragraph + one table or chart showing Tier 3 vs Tier 1/2 and, if possible, link to “more reported scores → higher pass rate” so the need for engagement is clear.
6. **Detail (optional):** Expandable table of all intervened students with all metrics above.

---

## 5. Next step

- **No code has been deployed.** Use this doc to align on definitions, audience, and which sections you want first (e.g. “just score trends + # tests reported” vs full report).
- When you’re ready, we can implement: (1) loading and parsing Interventions_initial.csv, (2) joining to test + tier data, (3) the summary metrics and tables, (4) optional charts for trends and “struggle/engagement.”
