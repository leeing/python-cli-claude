---
name: 代码风格参考 (Python CLI)
description: 代码风格参考：Python CLI 类型标注、日志、配置等编码规范示例
trigger: 当需要确认编码规范、类型标注、日志规范时
prerequisites: 无
---

# Skill: 代码风格参考 (Python CLI)

> 禁止清单见项目规范 §3，本文件仅提供「怎么做」的代码模式参考。

## 类型标注

```python
# ✅ 现代语法 (Python 3.10+)
def process(value: str | None) -> dict[str, int]: ...

# ❌ 禁止旧式
from typing import Optional, Union, Dict, List
def process(value: Optional[str]) -> Dict[str, int]: ...
```

## 配置管理

```python
# ✅ pydantic-settings
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    api_key: str
    debug: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# ❌ 禁止 os.environ
```

## 结构化日志

```python
import structlog
logger = structlog.get_logger()

# ✅ 键值对
logger.info("task_completed", task_id=task.id, duration=elapsed)

# ❌ 禁止
print(f"Task completed: {task.id}")
logger.info("Task " + task_id + " completed")
```

```python
# ✅ 标准库 logging 备选（无 structlog 依赖场景）
import logging
logger = logging.getLogger(__name__)
logger.info("task completed: task_id=%s duration=%.2fs", task_id, elapsed)
```

## 异常层次

```python
class AppError(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR"): ...

class ConfigError(AppError): ...
class InputError(AppError): ...
```

## 异步最佳实践

```python
# ✅ 并发执行
results = await asyncio.gather(fetch_a(), fetch_b(), fetch_c())

# ❌ 串行瀑布
a = await fetch_a()
b = await fetch_b()

# ❌ 同步阻塞
import requests  # 禁止
import time; time.sleep(5)  # 禁止

# ✅ 使用异步库
import httpx
async with httpx.AsyncClient() as client: ...
```

## pyproject.toml 关键配置

```toml
[tool.ruff]
target-version = "py312"
line-length = 120
src = ["src"]

[tool.ruff.lint]
select = [
    # ===== 核心必选 =====
    "E", "W",       # pycodestyle
    "F",            # Pyflakes
    "I",            # isort
    "B",            # flake8-bugbear
    "UP",           # pyupgrade
    "N",            # pep8-naming
    "S",            # Bandit 安全
    "SIM",          # flake8-simplify
    "PLR", "PLW",   # Pylint 重构/警告
    "TRY",          # tryceratops 异常
    "G",            # logging-format（禁止 f-string 日志）
    # ===== 建议项 =====
    "ARG",          # 未使用参数
    "C4",           # 推导式优化
    "C90",          # 圈复杂度
    "EM",           # 异常消息格式
    "FBT",          # 布尔参数陷阱
    "DTZ",          # 时区处理
    "PERF",         # 性能
    "ISC",          # 隐式字符串拼接
    "SLOT",         # __slots__ 优化
]

# 安全红线规则：禁止自动修复（手动审查后才可处理）
[tool.ruff.lint]
unfixable = ["S307", "S609", "S301", "S302", "S105", "S106", "S107"]

# 测试文件特殊宽松
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "PLR2004", "ARG001"]
"**/conftest.py" = ["ARG001"]
"**/__init__.py" = ["F401", "E402"]

# 圈复杂度上限
[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.mypy]
python_version = "3.12"
strict = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
```
