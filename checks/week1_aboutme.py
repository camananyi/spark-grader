"""Week 1: About Me"""
import ast
import re

from spark_grader import Failure, check, comments, crash_message, run, tree

TITLE = "Week 1: About Me"
FILE = "week1_aboutme.py"
# Numeric test answers, so programs that use int() or float() on an input still work
ANSWERS = ["4711", "5823", "6934", "7045", "8156", "9267", "1378", "2489"]
# Variable names that technically work but don't describe what they hold
VAGUE = re.compile(r"^([a-z]|[a-z]\d+|var\d*|variable\d*|input\d*|answer\d*|x\d*|temp\d*|thing\d*)$", re.I)
FILLER_COMMENT = re.compile(r"^#\s*(line\s*\d*|code|comment|todo|\d+|stuff|here)?\s*$", re.I)


def _input_calls(t):
    return [n for n in ast.walk(t)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "input"]


def _stored_inputs(t):
    names = []
    for node in ast.walk(t):
        if isinstance(node, ast.Assign) and _input_calls(node.value):
            names += [x.id for x in node.targets if isinstance(x, ast.Name)]
    return names


@check()
def exists():
    """week1_aboutme.py exists"""


@check(exists)
def compiles():
    """week1_aboutme.py has no syntax errors"""
    try:
        tree()
    except SyntaxError as e:
        raise Failure(f"Python couldn't read your file: line {e.lineno}: {e.msg}",
                      help="Check that line for a missing quote, bracket, or colon.")


@check(compiles)
def asks_four_questions():
    """asks the user for at least 4 pieces of information using input()"""
    count = len(_input_calls(tree()))
    if count < 4:
        raise Failure(f"found {count} input() call(s), expected at least 4",
                      help="Add more questions with input() until you have at least 4.")


@check(compiles)
def stores_in_named_variables():
    """stores each answer in a clearly named variable"""
    t = tree()
    stored = _stored_inputs(t)
    if len(stored) < len(_input_calls(t)):
        raise Failure("at least one input() is not saved in a variable",
                      help='Write each question like: favorite_food = input("What is your favorite food? ")')
    vague = [n for n in stored if VAGUE.match(n)]
    if vague:
        raise Failure(f"these variable names don't describe what they hold: {', '.join(vague)}",
                      help="Use names like first_name or favorite_color instead of x or var1.")


@check(compiles)
def runs_without_errors():
    """program runs without any errors"""
    result = run(ANSWERS)
    if result.crashed:
        raise crash_message(result, FILE)


@check(runs_without_errors)
def prints_paragraph_with_answers():
    """prints a short paragraph that uses every answer"""
    n = len(_input_calls(tree()))
    output = run(ANSWERS).output
    missing = [a for a in ANSWERS[:n] if a not in output]
    if missing:
        raise Failure(f"{len(missing)} of your {n} answers never showed up in what the program printed",
                      help="Make sure every variable is used in your print() paragraph.")
    # A paragraph needs real sentences around the answers, not just the answers themselves
    if len(re.findall(r"[A-Za-z']+", output)) < 15:
        raise Failure("the output looks like raw variables, not a paragraph",
                      help='Write full sentences around your variables, e.g. print(f"My name is {name} and I love {food}.")')


@check(compiles)
def has_comments():
    """has at least 2 meaningful comments"""
    meaningful = [c for c in comments()
                  if not FILLER_COMMENT.match(c) and len(re.findall(r"[A-Za-z]+", c)) >= 3]
    if len(meaningful) < 2:
        raise Failure(f"found {len(meaningful)} meaningful comment(s), expected at least 2",
                      help="Explain what your code does, e.g. # this asks the user for their name")
