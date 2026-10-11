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
        self.root = Path(root)
    def execute(self, name, args):
        try:
            if name == "read_file":
                content = (self.root / args["path"]).read_text(encoding="utf-8")
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
            else:
                return {"ok": False, "error": "未知工具：" + name}
        except (KeyError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            return{"ok": False, "error": str(e)}
        
ex = Executor(".")
print(ex.execute("run", {"argv": ["python", "-c", "print('hi')"]}))
# 期望：ok True, exit_code 0, stdout 'hi\r\n'

r = ex.execute("run", {"argv": ["python", "-c", "import sys; sys.exit(3)"]})
print(r["ok"], r["exit_code"])
# 期望：False 3

print(ex.execute("run", {"argv": ["python", "-c", "import time; time.sleep(40)"]}))
# 期望：等 30 秒后，ok False，不崩溃

print(ex.execute("run", {"argv": ["不存在的命令"]}))
# 期望：ok False，不崩溃（猜猜是哪个错误接住的？）

print(ex.execute("read_file", {"path": "agent_by_hand.py"})["ok"])
# 期望：True（确认旧功能没被改坏） 


# if __name__ == "__main__":
#     print(parse_action('{"type":"done","summary":"ok"}'))
#     print(parse_action('{"type":"tool","name":"read_file","args":{"path":"a.py"}}'))
#     for bad in ['hello', '[1,2]', '{"type":"tool","name":"x"}', '{"type":"done"}']:
#         try:
#             parse_action(bad)
#             print("❌ 应该报错但没报：", bad)
#         except ValueError as e:
#             print("✅ 正确拒绝：", bad, "→", type(e).__name__, e)
#     ex = Executor(".")
#     print(ex.execute("read_file", {"path": "agent_by_hand.py"})["ok"])   # True
#     print(ex.execute("read_file", {"path": "不存在.py"}))                # ok: False
#     print(ex.execute("fly", {}))                                        # 未知工具
#     print(ex.execute("read_file", {}))    
