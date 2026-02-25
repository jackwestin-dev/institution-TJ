# Internal analysis: distribution of test dates (Jan–Apr)

**Source:** institution-1-test-data.csv  
**Test types:** First Attempt, Second Exam Attempt  
**Months:** January, February, March, April

---

## Distribution (Jan–Apr only)

| Month     | First Attempt | Second Exam Attempt |
|----------|---------------|---------------------|
| January  | 0             | 0                   |
| February | 2             | 0                   |
| March    | 0             | 1                   |
| April    | 0             | 5                   |

**Totals (Jan–Apr):** First Attempt 2 | Second Exam Attempt 6

---

## All months (for context)

| Month     | First Attempt | Second Exam Attempt |
|----------|---------------|---------------------|
| February | 2             | 0                   |
| March    | 0             | 1                   |
| April    | 0             | 5                   |
| May      | 0             | 19                  |

---

## Note on data

- **First Attempt:** 54 rows total; **only 2 have a non-missing test_date** (both in February). The other 52 rows have blank `test_date`.
- **Second Exam Attempt:** 25 rows total; all have valid dates (6 in Jan–Apr, 19 in May).

To get a full Jan–Apr distribution for First Attempt, `test_date` would need to be filled for those 52 rows where it is currently missing.
