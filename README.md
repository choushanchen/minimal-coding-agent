# Minimal Coding Agent (built by hand)

A small software-engineering agent written from scratch in plain Python, with no frameworks. I built it to understand how coding agents work under the hood: the model proposes one JSON action at a time, the executor runs it inside a sandboxed workspace, and the result is fed back to the model.

## How it works

```
task ─▶ Agent.run() ─▶ model.complete(messages) ─▶ parse_action()
            ▲                                          │
            │                    {"type":"tool", ...}  ▼
            └──── observation (JSON) ◀──── Executor.execute()
                                  {"type":"done"} ─▶ summary
```

- **`parse_action`** validates every model reply against a strict schema: either `{"type":"tool","name":...,"args":{...}}` or `{"type":"done","summary":...}`. Malformed output is returned to the model as an error instead of crashing the loop.
- **`Executor`** provides three tools: `read_file`, `write_file` and `run`, which runs a command with a 30-second timeout and captures stdout, stderr and the exit code.
- **`Agent.run`** keeps the message history, enforces a `max_steps` limit and stops when the model returns `done`.

## Safety

- Paths must be relative. Absolute paths are rejected.
- Paths are resolved and must stay inside the workspace, which blocks `../` traversal.
- Subprocesses time out after 30 seconds. Known errors (missing keys, missing files, timeouts, bad paths) become structured observations.

## Demo

`demo_by_hand.py` creates a temporary project with a buggy `add()` (it subtracts) and three unit tests. A scripted model then drives the agent: it reads the file, runs the tests, sends one malformed reply to show error recovery, and reports the cause.

```bash
python demo_by_hand.py
```

```
[1]read_file
[2]run
{"status": "finished", "steps": 4, "summary": "add uses subtraction; 2 of 3 tests fail"}
```

## Next steps

- Plug in a real LLM provider in place of the scripted model.
- Add a `edit_file` tool with diff-based patches, so the agent can apply a fix and re-run the tests.

Requires Python 3.12 or later. The commit history shows the step-by-step build (`parse_action` → executor → run loop → sandboxing).
