import json
import tempfile
from pathlib import Path
from agent_by_hand import Agent, Executor

BUGGY = '''def add(a, b):
    return a - b
'''

TEST = '''import unittest
from calc import add

class AddTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(add(2, 3), 5)
    def test_negative(self):
        self.assertEqual(add(-2, -3), -5)
    def test_zero(self):
        self.assertEqual(add(0, 0), 0)
'''



class ScriptedModel:
    def __init__(self):
        self.replies = iter([
            {"type": "tool", "name": "read_file", "args": {"path": "calc.py"}},
            {"type": "tool", "name": "run", "args": {"argv": ["python", "-B", "-m", "unittest", "-v"]}},
            "我想想我能不能说点错话，用用其他形式，看看怎么报错",
            {"type": "done", "summary": "add 用了减法，3 个测试中 2 个失败"},
        ])

    def complete(self, messages):
        return json.dumps(next(self.replies), ensure_ascii=False)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "calc.py").write_text(BUGGY, encoding="utf-8")
        (Path(d) / "test_calc.py").write_text(TEST, encoding="utf-8")
        agent =  Agent(ScriptedModel(), Executor(d))
        print(json.dumps(agent.run("检查 add 函数为什么测试失败"), ensure_ascii=False, indent=2))