"""
Run all checks against a fresh throwaway database (never touches db.sqlite3).

    venv/bin/python scripts/checks/run.py            # everything
    venv/bin/python scripts/checks/run.py --quick    # skip the long random stress test

Exit code is 0 when everything passes, 1 otherwise.
"""
import logging
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT)]

tmp = tempfile.TemporaryDirectory()
os.environ["CHECKS_DB"] = os.path.join(tmp.name, "checks.sqlite3")
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

import django  # noqa: E402

django.setup()
logging.disable(logging.CRITICAL)  # expected 403/404/405s would otherwise flood the output

from django.core.management import call_command  # noqa: E402


def main():
    print("Building fresh database (migrate + seed_categories.py)...")
    call_command("migrate", verbosity=0)
    with open(ROOT / "seed_categories.py") as f, open(os.devnull, "w") as devnull:
        stdout, sys.stdout = sys.stdout, devnull
        try:
            exec(f.read(), {})
        finally:
            sys.stdout = stdout

    import check_redirects
    import check_rules
    import check_stress

    checks = [check_rules.run, check_redirects.run]
    if "--quick" not in sys.argv:
        checks.append(check_stress.run)

    failed = 0
    for check in checks:
        results = check()
        print(f"\n{results.section}")
        for name, passed, detail in results.items:
            print(f"  {'PASS' if passed else 'FAIL'}  {name}" + ("" if passed or detail == "" else f"   [{detail}]"))
            failed += not passed

    print(f"\n{'All checks passed.' if not failed else f'{failed} check(s) FAILED.'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
