"""Try a checks file on your own computer: python3 tools/test_checks.py week2_pennies my_file.py"""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "grader"))
import spark_grader

slug, student = sys.argv[1], sys.argv[2]
checks = open(os.path.join(os.path.dirname(__file__), "..", "checks", slug + ".py")).read()
t = time.time()
for r in spark_grader.grade(slug + ".py", open(student).read(), checks):
    face = {True: ":)", False: ":(", None: ":|"}[r["passed"]]
    print(face, r["description"])
    for line in (r["note"], r["help"]):
        if line:
            print("   ", line)
print(f"({time.time() - t:.1f}s)")
