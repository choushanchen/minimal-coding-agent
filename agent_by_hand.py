import json
from pathlib import Path


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
            else:
                return {"ok": False, "error": "未知工具：" + name}
        except (KeyError, FileNotFoundError) as e:
            return{"ok": False, "error": str(e)}
        
                              # 缺 path，也不能崩


if __name__ == "__main__":
    print(parse_action('{"type":"done","summary":"ok"}'))
    print(parse_action('{"type":"tool","name":"read_file","args":{"path":"a.py"}}'))
    for bad in ['hello', '[1,2]', '{"type":"tool","name":"x"}', '{"type":"done"}']:
        try:
            parse_action(bad)
            print("❌ 应该报错但没报：", bad)
        except ValueError as e:
            print("✅ 正确拒绝：", bad, "→", type(e).__name__, e)
    ex = Executor(".")
    print(ex.execute("read_file", {"path": "agent_by_hand.py"})["ok"])   # True
    print(ex.execute("read_file", {"path": "不存在.py"}))                # ok: False
    print(ex.execute("fly", {}))                                        # 未知工具
    print(ex.execute("read_file", {}))    
