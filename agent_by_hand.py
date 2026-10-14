import json
from pathlib import Path
import sys
import subprocess


def parse_action(raw:str) -> dict:
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("输出必须是 Json 对象")
    if obj.get("type") == "done" and isinstance(obj.get("summary"), str):
        return obj
    if obj.get("type") == "tool" and isinstance(obj.get("name"), str) and isinstance(obj.get("args"),dict):
        return obj
    else:
        raise ValueError("需要tool/name/args 或 done/summary 格式")

    
class Executor:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def path(self, name) ->Path:
        if not isinstance(name, str) or not name:
                raise ValueError("path 必须是非空字符串")
        if Path(name).is_absolute():
            raise ValueError("请使用相对路径")
        target = (self.root / name).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("路径超出工作区")
        return target

    def execute(self, name, args):
        try:
            if name == "read_file":
                content = self.path(args["path"]).read_text(encoding="utf-8")
                return {"ok": True, "output": content} 
            elif name == "run":
                argv = args["argv"]                     # 取出命令列表
                if argv[0] == "python":                         # 第一个是 "python" 吗？
                    argv[0] =  sys.executable                      # 替换成 sys.executable
                r = subprocess.run(argv, capture_output=True, cwd=self.root, timeout=30)         # 执行，三个参数
                return {"ok": r.returncode == 0,
                    "exit_code": r.returncode,
                    "stdout": r.stdout.decode("utf-8", errors="replace"),
                    "stderr": r.stderr.decode("utf-8", errors="replace"),
                    } 
            elif name == "write_file":
                p = self.path(args["path"])
                content = args["content"]  
                p.parent.mkdir(parents=True, exist_ok=True)  
                p.write_text(content,encoding="utf-8")
                return {"ok": True, "output": "written: " + args["path"]}
            else:
                return {"ok": False, "error": "未知工具：" + name}
        except (KeyError, FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
            return{"ok": False, "error": str(e)}
        
class Agent:
    def __init__(self, model, executor, max_steps=10):
        # 三个参数存到 self 上
        self.model, self.executor, self.max_steps = model, executor, max_steps

    def run(self, task):
        messages = [
            {"role": "system", "content": "你是一个软件工程 Agent，每次只输出一个 JSON 动作。"},
            {"role": "user", "content": task}
                    ]                      # 两条初始消息
        steps = 0
        while steps < self.max_steps:
            steps += 1
            raw = self.model.complete(messages)                         # 问模型
            messages.append({"role": "assistant", "content": raw})              # 记下模型的回复
            try:
                action = parse_action(raw)                  # 解析
                if action["type"] == "done":                       # 是 done 吗？
                    return {"status": "finished", "steps": steps, "summary": action["summary"]}
                print(f"[{steps}]{action["name"]}")                 # 打印 [步数] 工具名
                observation = self.executor.execute(action["name"], action["args"])             # 执行工具
            except ValueError as e:
                observation = {"ok": False, "error": "格式错误：" + str(e)}
            messages.append({"role": "user", "content": json.dumps(observation, ensure_ascii=False)})              # 把结果告诉模型
        return {"status": "step_limit", "steps": steps}                          # 步数用完


if __name__ == "__main__":
    # print(parse_action('{"type":"done","summary":"ok"}'))
    # print(parse_action('{"type":"tool","name":"read_file","args":{"path":"a.py"}}'))
    # for bad in ['hello', '[1,2]', '{"type":"tool","name":"x"}', '{"type":"done"}']:
    #     try:
    #         parse_action(bad)
    #         print("❌ 应该报错但没报：", bad)
    #     except ValueError as e:
    #         print("✅ 正确拒绝：", bad, "→", type(e).__name__, e)
    # ex = Executor(".")
    # print(ex.execute("read_file", {"path": "agent_by_hand.py"})["ok"])   # True
    # print(ex.execute("read_file", {"path": "不存在.py"}))                # ok: False
    # print(ex.execute("fly", {}))                                        # 未知工具
    # print(ex.execute("read_file", {}))    
    # ex = Executor(".")
    # print(ex.execute("run", {"argv": ["python", "-c", "print('hi')"]}))
    # # 期望：ok True, exit_code 0, stdout 'hi\r\n'

    # r = ex.execute("run", {"argv": ["python", "-c", "import sys; sys.exit(3)"]})
    # print(r["ok"], r["exit_code"])
    # # 期望：False 3

    # print(ex.execute("run", {"argv": ["python", "-c", "import time; time.sleep(40)"]}))
    # # 期望：等 30 秒后，ok False，不崩溃

    # print(ex.execute("run", {"argv": ["不存在的命令"]}))
    # # 期望：ok False，不崩溃（猜猜是哪个错误接住的？）

    # print(ex.execute("read_file", {"path": "agent_by_hand.py"})["ok"])
    # # 期望：True（确认旧功能没被改坏） 

    # class FakeModel:
    #     def __init__(self, replies):
    #         self.replies = iter(replies)
    #     def complete(self, messages):
    #         return next(self.replies)

    #     # 测试 1：正常流程，读文件 → 格式错误 → done
    # model = FakeModel([
    #     '{"type":"tool","name":"read_file","args":{"path":"agent_by_hand.py"}}',
    #     '我想想……',
    #     '{"type":"done","summary":"读完了"}',
    # ])
    # agent = Agent(model, Executor("."))
    # print(agent.run("读一下 agent_by_hand.py"))
    # # 期望：打印 [1] read_file
    # #       然后 {'status': 'finished', 'steps': 3, 'summary': '读完了'}

    # # 测试 2：模型一直不说 done，步数上限起作用
    # model = FakeModel(['{"type":"tool","name":"fly","args":{}}'] * 5)
    # agent = Agent(model, Executor("."), max_steps=2)
    # print(agent.run("测试步数上限"))
    # # 期望：打印 [1] fly 和 [2] fly
    # #       然后 {'status': 'step_limit', 'steps': 2}
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        Path(d, "secret.txt").write_text("这是工作区外面的秘密", encoding="utf-8")
        work = Path(d, "work")
        work.mkdir()

        ex = Executor(work)                   # 工作区是 d/work
        print(ex.execute("read_file", {"path": "../secret.txt"}))
        # 现在会怎样？
        print(ex.execute("read_file", {"path": "../secret.txt"}))
        # 期望：ok False，路径超出工作区

        print(ex.execute("write_file", {"path": "../hack.txt", "content": "x"}))
        # 期望：ok False，路径超出工作区

        print(ex.execute("read_file", {"path": "C:/Windows/win.ini"}))
        # 期望：ok False，请使用相对路径

        print(ex.execute("write_file", {"path": "sub/ok.txt", "content": "正常"}))
        # 期望：ok True（工作区里面的正常写入不受影响）