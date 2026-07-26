---
name: Hooks 配置与开发完全指南
description: Hooks 配置指南：安装、调试 Claude Code hooks
trigger: 当需要理解 hooks 架构、配置跨平台 hooks、调试 hook 行为、编写自定义检查脚本时
prerequisites: 项目已通过 init CLI 初始化（Claude Code）
---

# Skill: Hooks 配置与开发完全指南

> **本技能涵盖 claude-rules 的整个 hooks 生态**，包括架构、配置、编写、调试、跨平台支持。

---

## 第一部分：理解 Hooks 三层架构

### 概览

claude-rules 将规则分为三层：

```
Layer 1: CLAUDE.md / AGENTS.md
         ↓ (声明式约束)
Layer 2: Hooks (可执行检查)
         ├── PreToolUse    (在工具执行前阻止)
         ├── PostToolUse   (在写入/编辑后验证)
         ├── Stop          (任务完成前的最后检查)
         └── Notification  (日志和监控)
         ↓
Layer 3: Skills
         (过程式教学：「如何修复」代替「为什么失败」)
```

**为什么分三层？**
- **Layer 1 (MD)**：人类可读的规范，IDE 集成，作为权威参考
- **Layer 2 (Hooks)**：自动执行，立即反馈，减少人工检查负担
- **Layer 3 (Skills)**：关键问题的修复指南，减少 token 消耗

---

## 第二部分：全局 Hooks vs 项目 Hooks

### 全局 Hooks（安全基线）


**何时安装**：运行任何项目的 `init` CLI 时自动安装一次

**内容**：
| Hook | 事件 | 作用 | 平台 |
|------|------|------|------|
| `block-dangerous.py` | PreToolUse (Bash) | 拦截危险命令（git push, rm -rf, /etc/passwd 等） | Claude Code |
| `protect-files.py` | PreToolUse (Bash/Write/Edit/MultiEdit) | 保护关键文件（.git/, .env, secrets.json） | Claude Code |
| `check-secrets.py` | PreToolUse (Write/Edit/MultiEdit) | 检测硬编码凭证（API keys, AWS AKIA, PEM）| Claude Code |
| `check-type-suppression.py` | PostToolUse (Write/Edit/MultiEdit) | 计数 `# type: ignore` 不超过 3 | Claude Code |
| `log-commands.py` | PostToolUse (Bash) | 记录执行的命令到 `~/.claude/hooks-logs/commands-YYYY-MM-DD.log` | Claude Code |

**作用**：所有项目共享，无需重复配置。即使未初始化项目，全局 hooks 也会保护用户。

### 项目 Hooks（栈特定质量门禁）

**位置**：`..claude/hooks/`（项目根目录）

**何时安装**：运行项目的 `init` CLI 时安装，基于项目类型

**示例**（python-cli 项目）：
| Hook | 事件 | 检查项 |
|------|------|--------|
| `check-constraints.py` | PostToolUse (Write/Edit/MultiEdit) | 第三方 import 限制、structlog vs print、pydantic-settings |
| `check-scaffold.py` | PostToolUse (Write/Edit/MultiEdit) | 项目目录结构完整性（src/, tests/ 等） |
| `auto-gate.py` | Stop | 完整 lint+typecheck+test 流程 |

---

## 第四部分：配置 Hooks（settings.json 编写）

### 事件类型映射

```
PreToolUse
  ├─ Bash              ← 执行命令前（检查危险操作）
  └─ 其他工具（如需定制）

PostToolUse
  ├─ Write             ← 创建/覆盖文件后
  ├─ Edit              ← 编辑文件后
  ├─ MultiEdit         ← 批量编辑后
  └─ 其他工具

Notification           ← 不阻断，仅用于日志
  └─ Bash

Stop                   ← AI 任务完成时
  └─ （无 matcher，全局触发）
```

### 添加新 Hook 的步骤

**场景**：你想在编辑 TypeScript 文件时自动检查 ESLint

**步骤 1**：创建 hook 脚本（见第五部分）

例如 `~/.claude/hooks/check-eslint.py`

**步骤 2**：更新 `settings.claude.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/check-eslint.py",
            "timeout": 15                    // 足够运行 eslint
          }
        ]
      }
    ]
  }
}
```


```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "name": "check-eslint",         // ← 必需！
            "type": "command",
            "timeout": 15000                // ← 毫秒！
          }
        ]
      }
    ]
  }
}
```

### 常见 Matcher 模式

```json
{
  "matcher": "Bash"                           // 仅 Bash 工具
}

{
  "matcher": "Write|Edit|MultiEdit"          // 任何文件写入操作
}

{
  "matcher": "Edit"                           // 仅编辑（不包括新创建）
}

{
  "matcher": "Bash.*delete"                   // 正则匹配（高级）
}
```

---

## 第五部分：编写 Hook 脚本

### Hook 脚本的标准模板

所有 hook 脚本应遵循以下结构：

```python
#!/usr/bin/env python3
"""
Hook script: check-custom-rule

触发事件：PostToolUse (Write|Edit|MultiEdit)
作用：检查自定义规则是否满足
返回值：0=通过，2=失败（阻止操作），其他=错误
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# ============================================================================
# 日志支持（跨平台）
# ============================================================================

def hook_log(event: str, hook_name: str, status: str, message: str = "") -> None:
    """
    记录 hook 执行结果到日志文件
    
    支持两种项目环境变量：
    - CLAUDE_PROJECT_DIR（Claude Code）
    
    日志格式：
      2026-04-06 09:20:01 | PostToolUse | check-custom-rule | PASS:file.py
      2026-04-06 09:20:02 | PostToolUse | check-custom-rule | FAIL:Reason here
    """
    project_dir = os.getenv("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return
    
    log_dir = Path(project_dir) / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} | {event:<12} | {hook_name:<30} | {status}"
    if message:
        log_entry += f":{message}"
    
    with open(log_dir / "hooks.log", "a") as f:
        f.write(log_entry + "\n")

# ============================================================================
# 路径安全检查（防止目录遍历攻击）
# ============================================================================

def is_safe_path(file_path: str) -> bool:
    """
    验证 file_path 在当前项目目录内，防止 ../../../../etc/passwd 攻击
    
    使用 realpath() 解析符号链接，确保路径真实存在于项目内
    
    Args:
        file_path: 待检查的文件路径（可能是相对路径）
    
    Returns:
        True if 路径在项目内，False 否则
    """
    try:
        real_path = os.path.realpath(file_path)
        cwd = os.path.realpath(".")
        return real_path.startswith(cwd + os.sep) or real_path == cwd
    except (OSError, ValueError):
        return False

# ============================================================================
# 实际检查逻辑
# ============================================================================

def check_custom_rule(file_path: str, file_content: str) -> list[str]:
    """
    检查文件是否满足自定义规则
    
    Args:
        file_path: 待检查的文件路径
        file_content: 文件内容
    
    Returns:
        错误列表，空列表 = 通过
        例：["Line 10: 禁止使用 eval()"]
    """
    errors = []
    
    # 示例：检查禁止 eval()
    for line_no, line in enumerate(file_content.split("\n"), 1):
        if "eval(" in line:
            errors.append(f"Line {line_no}: 禁止使用 eval()，改用 ast.literal_eval() 或其他安全方案")
    
    return errors

# ============================================================================
# Main 入口
# ============================================================================

def main():
    """
    Hook 主入口
    
    参数从环境变量读取（由 Claude Code 注入）：
      - CLAUDE_TOOL_INPUT_file_path: 文件路径
      - CLAUDE_TOOL_INPUT_file_content: 文件内容
    
    返回值：
      0 = 通过（continue)
      2 = 失败（阻止操作）
      其他 = 错误（记录但不阻止）
    """
    # 获取参数
    file_path = os.getenv("CLAUDE_TOOL_INPUT_file_path", "")
    file_content = os.getenv("CLAUDE_TOOL_INPUT_file_content", "")
    
    if not file_path or not file_content:
        # 环境变量未提供时，尝试从命令行参数读取（向后兼容）
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
        if len(sys.argv) > 2:
            file_content = sys.argv[2]
    
    # 路径安全检查
    if not is_safe_path(file_path):
        hook_log("PostToolUse", "check-custom-rule", "FAIL", "Path traversal detected")
        sys.exit(2)
    
    # 执行检查
    errors = check_custom_rule(file_path, file_content)
    
    if errors:
        hook_log("PostToolUse", "check-custom-rule", "FAIL", file_path)
        for error in errors:
            print(f"❌ {error}")
        sys.exit(2)
    
    hook_log("PostToolUse", "check-custom-rule", "PASS", file_path)
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### 关键设计模式

#### 1. 环境变量注入

Claude Code 通过环境变量传递参数：

```python
file_path = os.getenv("CLAUDE_TOOL_INPUT_file_path", "")
file_content = os.getenv("CLAUDE_TOOL_INPUT_file_content", "")
```

#### 2. 路径安全（防止目录遍历）

```python
def is_safe_path(file_path: str) -> bool:
    try:
        real_path = os.path.realpath(file_path)    # 解析符号链接
        cwd = os.path.realpath(".")
        return real_path.startswith(cwd + os.sep) or real_path == cwd
    except (OSError, ValueError):
        return False
```

**为什么必需**？
- 攻击者可能输入 `"../../../../etc/passwd"` 尝试读取系统文件
- `realpath()` 会解析所有 `..` 和符号链接，暴露真实路径
- 检查 `startswith(cwd)` 确保路径在项目范围内

#### 3. 跨平台日志

```python
def hook_log(event: str, hook_name: str, status: str, message: str = "") -> None:
    # 支持两种项目类型
    project_dir = os.getenv("CLAUDE_PROJECT_DIR")
    log_dir = Path(project_dir) / ".claude" / "logs"
    # ... 记录到统一位置
```

#### 4. 返回值约定

```python
sys.exit(0)   # ✅ 通过，继续执行
sys.exit(2)   # ❌ 失败，阻止操作（标准惯例）
sys.exit(1)   # ⚠️ 错误，记录但不阻止
```

---

## 第六部分：调试 Hooks

### 查看 Hook 日志

```bash
# 查看所有 hook 执行记录
cat .claude/logs/hooks.log

# 输出示例：
# 2026-04-06 09:20:01 | PreToolUse   | block-dangerous         | PASS
# 2026-04-06 09:20:02 | PostToolUse  | check-constraints       | FAIL:script.py
# 2026-04-06 09:22:30 | Stop         | auto-gate               | PASS
```

### Hook 失败时的调试步骤

**问题**：提交代码时 Hook 失败，不知道原因

**调试步骤**：

1. **查看错误消息**
   ```
   ❌ Line 25: 禁止使用 print()，改用 logging 模块
   ```

2. **定位失败原因**
   - 阅读错误消息中的文件路径和行号
   - 搜索对应代码行

3. **修复问题**
   ```python
   # ✗ 错误
   print("Debug:", result)
   
   # ✓ 修复
   import logging
   logger = logging.getLogger(__name__)
   logger.debug(f"Debug: {result}")
   ```

4. **重新尝试**
   - 保存文件，系统自动重新运行 hook
   - 如果还是失败，检查修复是否完全

### 常见问题排查

**问题 1：Hook 超时**
```
🚫 Hook timeout (5s exceeded)
```
- 原因：检查逻辑太复杂或文件过大
- 解决：优化检查函数，或增加 `timeout` 值

**问题 2：Hook 环境变量缺失**
```
⚠️ file_path environment variable not set
```
- 原因：Hook 平台支持不完整
- 解决：检查 Claude Code 版本，确保支持 hook

**问题 3：路径安全错误**
```
❌ Path traversal detected: ../../../../etc/passwd
```
- 原因：Hook 脚本防护工作（实际上是好事）
- 解决：检查 Hook 参数是否被篡改

---

## 第七部分：init.py 工作流

### init.py 如何安装 Hooks

当你运行 `python3 init.py <template> <project_dir>` 时：

```
1. copy_config_files()
   ├─ 复制 CLAUDE.md / AGENTS.md 到项目
   └─ 复制 pyproject.toml 等工具链配置

2. copy_skills()
   └─ 复制 skill 文档到 .claude/skills/ 和 .agents/skills/

3. copy_global_hooks()  ← ⭐ 新增（2026-04-06）
   ├─ 复制全局 hook 脚本（block-dangerous.py 等）
   └─ 按 matcher 级别追加全局 hook 配置到 ~/.claude/settings.json

4. copy_hooks()
   ├─ 创建 .claude/hooks/（项目级）
   ├─ 复制项目 hook 脚本（check-constraints.py 等）
   └─ 按 matcher 级别追加项目 hook 配置到 ./.claude/settings.json

5. copy_ci()
   └─ 复制 CI 配置（GitHub Actions / GitLab CI）
```

### hooks 配置合并的实际行为

**旧行为（浅合并）**：
```python
existing_hooks.update(new_hooks)  # ← 同名 key 被覆盖！
```
问题：多次运行 init.py 或安装多个项目会丢失之前的 hook 配置

**当前行为（按 matcher 级追加）**：
```python
# 按事件类型 (PreToolUse, PostToolUse, Stop, Notification) 追加
for event_name, new_matchers in new_hooks.items():
    if event_name not in existing_hooks:
        existing_hooks[event_name] = []
    
    # 检查重复 matcher，避免添加相同的规则两次
    existing_patterns = {m.get("matcher") for m in existing_hooks[event_name]}
    for matcher in new_matchers:
        if matcher.get("matcher") not in existing_patterns:
            existing_hooks[event_name].append(matcher)  # ← 追加！
```

**效果**：
- ✅ 保留目标 `settings.json` 中的非 hook 配置
- ✅ 相同 event 下不会重复追加相同 `matcher` 的配置块
- ⚠️ 相同 event + matcher 的 hooks 不会继续做 hook-by-hook 深度合并

---

## 第八部分：扩展场景

### 场景 1：添加企业安全检查

**需求**：检查代码中是否硬编码了企业内网 IP

**步骤**：

1. 创建 `~/.claude/hooks/check-internal-ips.py`
2. 添加到 `~/.claude/settings.json`：
   ```json
   {
     "hooks": {
       "PostToolUse": [
         {
           "matcher": "Write|Edit",
           "hooks": [
             {
               "type": "command",
               "command": "python3 ~/.claude/hooks/check-internal-ips.py",
               "timeout": 5
             }
           ]
         }
       ]
     }
   }
   ```

### 场景 2：自定义 Auto Gate 步骤

**需求**：在 lint 之前运行 security scanner

**方法**：编辑项目的 `hooks/auto-gate.py`，修改 `main()` 函数：

```python
def main():
    steps = [
        ("bandit", ["python3", "-m", "bandit", "-r", "src/"]),  # ← 新增
        ("ruff format", ["ruff", "format", "--check", "."]),
        ("ruff check", ["ruff", "check", "."]),
        ("mypy", ["mypy", "src/"]),
        ("pytest", ["pytest", "tests/", "-v"]),
    ]
    
    for step_name, cmd in steps:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            print(f"❌ {step_name} failed")
            sys.exit(2)
```

### 场景 3：针对特定文件类型的检查

**需求**：仅检查 `.yml` 和 `.yaml` 文件的格式

**方法**：在 hook 脚本中过滤：

```python
def main():
    file_path = os.getenv("CLAUDE_TOOL_INPUT_file_path", "")
    
    # 仅检查 YAML 文件
    if not file_path.endswith((".yml", ".yaml")):
        sys.exit(0)  # 跳过其他文件
    
    # ... 执行 YAML 检查
```

---

## 第九部分：最佳实践

### DO ✅

- **明确的错误消息**：告诉用户「做什么」和「为什么」
  ```python
  print("❌ Line 42: 禁止 eval()，改用 ast.literal_eval()")
  ```

- **快速失败**：重的检查放在最后
  ```python
  # 先检查简单的（文件类型、路径）
  # 再检查复杂的（AST 解析、类型检查）
  ```

- **路径安全**：始终用 `is_safe_path()` 验证输入
  ```python
  if not is_safe_path(file_path):
      sys.exit(2)
  ```

- **跨平台支持**：同时配置 `settings.claude.json` 和
  ```json
  // settings.claude.json: timeout 用秒，无 name 字段
  //: timeout 用毫秒，必需 name 字段
  ```

### DON'T ❌

- **泛型异常捕获**
  ```python
  # ✗ 错误
  try:
      result = some_operation()
  except Exception:
      pass  # 吞掉所有错误！
  
  # ✓ 正确
  try:
      result = some_operation()
  except (FileNotFoundError, ValueError) as e:
      print(f"Expected error: {e}")
      sys.exit(2)
  ```

- **硬编码路径**
  ```python
  # ✗ 错误
  log_file = "/home/user/.claude/logs/hooks.log"
  
  # ✓ 正确
  log_file = Path.home() / ".claude" / "logs" / "hooks.log"
  ```

- **过长的超时**
  ```python
  # ✗ 错误（等 5 分钟！）
  "timeout": 300
  
  # ✓ 正确（等 15 秒，足够运行 typecheck）
  "timeout": 15
  ```

- **混淆平台配置**
  ```python
  # ✗ 错误：在 settings.claude.json 中使用毫秒
  "timeout": 5000  // Claude Code 会等 83 分钟！
  
  # ✓ 正确
  # settings.claude.json:  "timeout": 5      // 秒
  #:  "timeout": 5000   // 毫秒
  ```

---

## 第十部分：快速参考

### 环境变量映射表

| 变量 | 来源 | 说明 |
|------|------|------|
| `CLAUDE_TOOL_INPUT_file_path` | Claude Code | 待检查文件的路径 |
| `CLAUDE_TOOL_INPUT_file_content` | Claude Code | 文件内容 |
| `CLAUDE_PROJECT_DIR` | Claude Code | 项目根目录 |

### 返回值约定

| 返回值 | 含义 | 示例 |
|------|------|------|
| `0` | ✅ 通过 | hook 检查成功 |
| `2` | ❌ 失败，阻止操作 | 检查到规则违反 |
| `1` | ⚠️ 错误，但不阻止 | 脚本崩溃或环境问题 |

### 事件类型速查

| 事件 | Matcher | 何时触发 | 能否修复 |
|------|---------|---------|---------|
| `PreToolUse` | `Bash` | 执行命令**前** | 否（拦截） |
| `PostToolUse` | `Write\|Edit\|MultiEdit` | 写入/编辑**后** | 可（提示修复）|
| `Stop` | （无） | AI 任务**完成前** | 可（重新运行）|
| `Notification` | `Bash` | 命令执行**后** | 否（仅记录）|

### Timeout 值指南

| Hook 类型 | 典型耗时 | 建议 timeout |
|----------|---------|------------|
| 简单正则检查 | <100ms | 5s / 5000ms |
| 文件读写、目录扫描 | 100-500ms | 10s / 10000ms |
| Lint 检查（ruff, eslint） | 500ms-3s | 15s / 15000ms |
| 完整质量门禁（lint+type+test） | 10-60s | 300s / 300000ms |

---

## 总结

**要点回顾**：

1. ✅ Hooks 分为全局（安全基线）和项目（质量门禁）两级
2. ✅ Claude Code 配置格式（timeout 单位）
3. ✅ Hook 脚本必须包含路径安全检查和跨平台日志支持
4. ✅ init.py 会保留其他 settings 键，并按 matcher 级别追加 hook 配置
5. ✅ 调试 hook 从查看日志开始，定位错误后修复代码并重试

**下一步**：
- 需要添加新 hook？按第五部分的模板编写，参考现有脚本
- Hook 失败了？从 `.claude/logs/hooks.log` 开始排查
- 想要跨平台支持？同时配置 `settings.claude.json` 和
