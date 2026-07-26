---
name: 新建 CLI 功能
description: 为 Python CLI 项目添加新命令或子命令的标准开发流程
trigger: 当用户要求添加新的 CLI 命令、子命令或选项时
prerequisites: 项目已配置 Click/Typer 入口
---

# Skill: 新建 CLI 功能

## 工作流

### 1. 理解需求
- 明确命令名称、参数（`--option` / positional arg）和退出码语义
- 确认输出目标：机器可解析结果写 `stdout`，日志/进度写 `stderr`

### 2. 在 Service 层实现业务逻辑

```python
# src/project_name/services/<feature>.py
import structlog

log = structlog.get_logger()

def run_feature(param: str) -> list[str]:
    """业务逻辑与 CLI 解耦 — 此函数可被单元测试直接调用。"""
    log.info("running_feature", param=param)
    ...
```

### 3. 添加 CLI 命令（薄适配层）

```python
# src/project_name/commands/<feature>.py
import sys
import click
from project_name.services.feature import run_feature

@click.command()
@click.argument("param")
@click.option("--verbose", is_flag=True)
def feature_cmd(param: str, verbose: bool) -> None:
    """单行说明（Google docstring 格式）。"""
    try:
        results = run_feature(param)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    for line in results:
        click.echo(line)
```

### 4. 注册命令

```python
# src/project_name/main.py
from project_name.commands.feature import feature_cmd

cli.add_command(feature_cmd, name="feature")
```

### 5. 编写测试

```python
# tests/test_feature_cmd.py
from click.testing import CliRunner
from project_name.main import cli

def test_feature_happy_path():
    runner = CliRunner()
    result = runner.invoke(cli, ["feature", "my-param"])
    assert result.exit_code == 0
    assert "expected output" in result.output

def test_feature_invalid_input():
    runner = CliRunner()
    result = runner.invoke(cli, ["feature", "bad"])
    assert result.exit_code == 1
```

### 6. 验证

```bash
uv run ruff format .
uv run ruff check --fix .
uv run mypy src/
uv run pytest tests/ -v
```

## 规则

- CLI 命令只做参数解析 + 调用 Service，不含业务逻辑
- `sys.exit(1)` 表示业务错误，`sys.exit(2)` 表示参数错误（Click 会自动处理后者）
- 机器可解析输出写 `stdout`（`click.echo`），日志/警告写 `stderr`（`click.echo(err=True)` 或 structlog）
- 禁止 `time.sleep` — 轮询逻辑改用事件驱动；禁止 `requests` — 改用 `httpx` + `async`
- 非 TTY 环境（CI、管道）禁止交互式提示

## 检查清单

- [ ] 业务逻辑在 `services/` 层，命令只做参数解析和调用
- [ ] 有 happy path 测试 + 错误路径测试
- [ ] 命令已在 `main.py` 注册
- [ ] `--help` 输出有意义的说明文本
- [ ] Auto Gate 全部通过（ruff + mypy + pytest）
