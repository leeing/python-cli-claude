# Python CLI 项目规范

> **技术栈专属规范。** 通用规范见全局规范（Global Rules）。
> 代码模式示例见 skills 目录 `code-style/`；约束由 `hooks/` 自动检查和拦截。

---

## 1. 工具链

弃用 `pip`, `venv`, `setup.py`, `requirements.txt`。

| 工具 | 用途 | 替代 |
|------|------|------|
| **uv** | 版本管理、环境隔离、依赖同步 | pip, venv, pyenv |
| **Ruff** | 检查 + 格式化 | Black, isort, flake8 |
| **Mypy** | 类型检查（CI 强制，strict 模式） | - |

---

## 2. 项目结构

```
project/
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── main.py           # CLI 入口
│       └── utils.py
├── tests/
│   └── test_main.py
├── pyproject.toml
└── README.md
```

**⚠️ 初始脚手架要求（弱模型适配）**
当你第一次创建项目时，必须创建 `pyproject.toml` 等核心配置。系统 Hook (`check-scaffold.py`) 包含了标准的 TOML 模板，如有配置遗漏，请直接根据 Hook 报错里提供的模板内容进行 Copy-Paste。

---

## 3. 禁止清单

以下约束大部分由 hooks 自动拦截，违规时错误信息会告知修复方式：

- **安全红线规则禁止 `# noqa` 豁免** → `check-constraints.py`
- **直接访问 `os.environ`** → `check-constraints.py`（使用 `pydantic-settings`）
- **`os.path` 路径操作** → `check-constraints.py`（使用 `pathlib.Path`）
- **`print` 调试** → `check-constraints.py`（使用 `structlog`）
- **`# type: ignore` 累积 >3** → `check-constraints.py`
- **文件超 1000 行** → `check-constraints.py`

### Hooks 不覆盖（必须人工遵守）

- **旧式类型标注**：禁止 `Optional`/`Union`/`List`/`Dict`，使用 `str | None` / `list[str]`
- **同步阻塞 IO**：禁止 `requests`/`time.sleep`，使用 `httpx` + `async`
- **logging 禁止 f-string**：使用参数化格式或 structlog 键值对
- **泛型 `except Exception`**：只捕获具体预期异常
- **禁止 `assert` 做业务验证**：使用 `raise ValueError` 等显式校验
- **公共 API 必须有 docstring**：Google 风格
- **Ruff 规则组完整性**：pyproject.toml select 必须包含完整规则组（见 code-style skill）
- **代码体积**：单函数/方法 ≤ 100 行（文件级由 hook 检查）
- **行宽 120**：Ruff `line-length = 120`

---

## 4. Hook 失败恢复（必读）

本项目配置了自动质量门禁（hooks）。当你看到 `🚫 Auto Gate BLOCKED` 时：

1. **不要停止**——这是让你修复后重试，不是终止信号
2. 阅读每条 `❌` 错误消息，定位失败的检查项
3. 修复代码中的问题
4. 修复后系统会自动重新运行检查

**最多允许 3 轮自修复**。3 轮后仍未通过，告知用户现状并列出剩余失败项。

---

## 5. 常用命令

| 命令 | 用途 |
|------|------|
| `uv run python -m project_name.main` | 运行入口 |
| `uv run pytest tests/ -v` | 运行测试 |
| `uv run ruff format .` | 格式化 |
| `uv run ruff check --fix .` | Lint 并修复 |
| `uv run mypy src/` | 类型检查 |
| `uv add <package>` | 添加依赖 |

---

## 6. 项目特有陷阱

- **`time.sleep` 阻塞事件循环**：禁止在异步上下文中使用 `time.sleep`，改用 `asyncio.sleep`；同步轮询逻辑考虑用事件驱动替代
- **Click 参数校验时机**：不要在 `@click.command` 回调内部做复杂 IO，先用 `callback=` 或 `is_eager=True` 对参数做格式校验，再进入主逻辑
- **stderr vs stdout 分离**：进度/日志输出写 `stderr`（`structlog` 默认），机器可解析的结果写 `stdout`，确保 CLI 在管道场景中可被正确消费
- **非 0 退出码规范**：使用 `sys.exit(1)` 表示业务错误，`sys.exit(2)` 表示使用错误（参数错误），Click 会自动处理参数错误的退出码
