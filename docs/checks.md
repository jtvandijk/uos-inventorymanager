# Checks

Automated checks that click through the app the way volunteers and admins do, and confirm the rules still hold. Run them on your laptop **before pushing** any change.

```bash
venv/bin/python scripts/checks/run.py           # everything (~15 seconds)
venv/bin/python scripts/checks/run.py --quick   # skip the random stress test
```

Every line should say `PASS` and the last line `All checks passed.` A `FAIL` line says which rule broke, often with a detail in `[...]`.

The checks build their own throwaway database each time (migrations + `seed_categories.py`), so they never touch `db.sqlite3` and give the same result on any machine.

## What's covered

| File | What it checks |
| --- | --- |
| `check_rules.py` | One check per rule: size lists, two-miss lapse, long-overdue extension, packing, special-request queue, cancel, re-assign (with/without spare, regular/special), delete, collect, pack all, permissions |
| `check_redirects.py` | Every button on the item page, submitted like a browser: lands on the right page, Back still returns to where you came from, plain visits and missing CSRF tokens are refused |
| `check_stress.py` | Hundreds of random actions by several users, plus days passing with the daily jobs; after every step it checks the data is still consistent and no page errors |

## Adding a check

When a bug turns up, add a check that fails because of it, fix the bug, and watch it pass. Most go in `check_rules.py` as a small block:

```python
reset_stock()
[c1] = add(coat)
reserve(c1, "Ann")
V.post(f"/inventory/collect/{c1.id}/")
R.ok("collect: given, name kept", fresh(c1).status == "given")
```

`A` and `V` are an admin and a volunteer; helpers like `add`, `reserve`, `new_sr`, `age_reservations` and `run_daily_jobs` are at the top of the file and in `common.py`. A rule that should hold *all the time* (not just after one action) belongs in `_broken_rules()` in `check_stress.py`.
