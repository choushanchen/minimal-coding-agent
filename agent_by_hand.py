import json
def parse_action(raw:str) -> dict:
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("输出必须是 Json 对象")
    if obj.get("type") == "done" and isinstance(obj.get("summary"), str):
        return obj
    if obj.get("type") == "tool" and isinstance(obj.get("name"), str) and isinstance(obj.get("args"),dict):
        return obj
    else:
        raise ValueError
if __name__ == "__main__":
    print(parse_action('{"type":"done","summary":"ok"}'))
    print(parse_action('{"type":"tool","name":"read_file","args":{"path":"a.py"}}'))
    for bad in ['hello', '[1,2]', '{"type":"tool","name":"x"}', '{"type":"done"}']:
        try:
            parse_action(bad)
            print("❌ 应该报错但没报：", bad)
        except ValueError as e:
            print("✅ 正确拒绝：", bad, "→", e)