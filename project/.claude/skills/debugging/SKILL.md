---
name: 系统化调试
description: 系统化调试：复现问题、定位根因、修复验证的调试流程
trigger: 当遇到 Bug、测试失败或异常行为时
prerequisites: 问题已可复现
---

# Skill: 系统化调试 (Systematic Debugging)

## 核心原则

**先诊断，后修复。** 禁止在未理解根因的情况下尝试修复。

## 调试流程

```
REPRODUCE → ISOLATE → DIAGNOSE → FIX → VERIFY → DOCUMENT
```

### 1. 复现问题

在动手修复之前，必须先稳定复现：

```bash
# 运行失败的测试
uv run pytest tests/test_xxx.py::test_name -v

# 如果是运行时错误，用最小参数启动
uv run python -m project_name.main
```

**记录复现条件：**
- 触发命令 / 请求
- 错误信息（完整 traceback）
- 环境差异（本地 vs CI、Python 版本、依赖版本）

### 2. 缩小范围

**禁止：** 一次修改多个文件来"试试看"

```python
# ✅ 用最小代码片段隔离问题
import asyncio
from project_name.lib.db import async_session_maker

async def debug():
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT 1"))
        print(result.scalar())

asyncio.run(debug())
```

### 3. 诊断根因

**按优先级检查：**

| 顺序 | 检查项 | 命令 |
|------|--------|------|
| 1 | 类型错误 | `uv run mypy src/` |
| 2 | 导入/依赖问题 | `uv run python -c "from module import X"` |
| 3 | 依赖版本冲突 | 检查 `uv.lock` 和 `pyproject.toml` |
| 4 | 异步问题 | 检查是否混用 sync/async |
| 5 | 数据问题 | 检查输入数据和配置 |

**常见陷阱：**

- **循环导入**：顶层导入形成环形依赖 → 用函数内延迟导入
- **异步阻塞**：在 async 函数中调用 `time.sleep()` / `requests.get()`
- **路径问题**：硬编码路径 vs `pathlib.Path` 相对路径

### 4. 修复

- 一次只改一个地方
- 改完立即运行相关测试确认修复
- 如果修复引入新问题，回退并重新诊断

### 5. 验证

```bash
# 运行失败的测试
uv run pytest tests/test_xxx.py::test_name -v

# 运行全量测试确认无回归
uv run pytest tests/ -v

# 类型检查
uv run mypy src/
```

### 6. 记录

修复后在 commit message 中说明根因：

```
fix(auth): resolve token validation failure

Root cause: JWT decode used wrong algorithm constant.
The `ALGORITHM` variable was "HS512" but tokens were
signed with "HS256".
```

## AI 自诊断清单

**在向用户求助前，必须先完成以下所有步骤：**

- [ ] 运行 `git diff` 查看最近变更，确认是否由近期修改引入
- [ ] 运行失败命令并保存完整 traceback
- [ ] 检查 `uv.lock` 是否与 `pyproject.toml` 同步（`uv sync`）
- [ ] 检查 `.env` 配置是否完整（对比 `.env.example`）
- [ ] 运行 `uv run mypy src/` 确认是否有隐含类型错误
- [ ] 运行 `uv run ruff check .` 确认是否有 lint 问题
- [ ] 以上全部完成后仍无法解决 → 向用户报告，附带已尝试的方案和失败原因
