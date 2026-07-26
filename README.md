# Python CLI — Claude Code 规范模板

> 适用于 **Claude Code** 的 Python CLI 项目规范模板，包含 AI 行为规则、自动化质量门禁（Hooks）和操作流程指南（Skills）。
> 设计目标：**让 AI 在无人监督的情况下也能写出符合工程规范的代码。**

---

## 目录

- [为什么用这套模板？](#为什么用这套模板)
- [快速安装](#快速安装)
- [仓库结构](#仓库结构)
- [设计原理](#设计原理)
  - [整体架构](#整体架构)
  - [CLAUDE.md —— AI 的行为准则](#claudemd--ai-的行为准则)
  - [Skills —— AI 的操作手册](#skills--ai-的操作手册)
  - [Hooks —— 自动化质量门禁](#hooks--自动化质量门禁)
  - [Auto Gate 详解](#auto-gate-详解)
- [Hooks 参考](#hooks-参考)
- [Skills 参考](#skills-参考)
- [使用示例](#使用示例)
- [常见问题](#常见问题)

---

## 为什么用这套模板？

本模板**强制推行现代 Python 技术栈**。部署这套 hooks 和规范后，你的项目会自然使用目前业界最新的工具链：

### 工具链对比：传统 vs 现代

| 环节 | 传统方案 ❌ | 本模板方案 ✅ | 为什么更好 |
|------|-----------|-------------|-----------|
| **包管理** | `pip` + `venv` + `requirements.txt` | **uv** + `pyproject.toml` | 单一工具管理 Python 版本、虚拟环境、依赖锁定，速度比 pip 快 10-100 倍 |
| **格式化** | Black / autopep8 | **Ruff** (format) | 用 Rust 写的 Python linter+formatter，速度比 Black 快 30 倍以上 |
| **Lint** | flake8 / isort / pylint | **Ruff** (check) | 一个工具替代 flake8 + isort + 数十个插件，配置集中在 pyproject.toml |
| **类型检查** | 裸写 Python / 偶尔用 mypy | **Mypy** (`strict = true`) | strict 模式强制完整类型标注，编译期发现类型错误 |
| **测试** | unittest / nose | **pytest** | 现代 Python 测试的事实标准，更简洁的断言和 fixture 系统 |
| **日志** | `print()` / `logging` + f-string | **structlog** | 结构化日志，输出 JSON 格式，天然适配 ELK / Datadog 等采集系统 |
| **配置管理** | `os.environ` 散落各处 | **pydantic-settings** | 类型安全的配置加载，自动校验环境变量，IDE 友好 |
| **HTTP 请求** | `requests` (同步阻塞) | **httpx** (async) | 原生 async/await 支持，不阻塞事件循环 |
| **类型标注** | `Optional[str]`, `List[dict]` | `str \| None`, `list[dict]` | Python 3.10+ 原生语法，更简洁，不需要从 typing 导入 |
| **路径操作** | `os.path.join(...)` | `pathlib.Path` | 面向对象的路径 API，`/` 操作符拼接，跨平台自动适配 |

### 几个关键原则

**1. 只保留最好的一个。** Python 生态圈常常有多个方案并存（pipenv vs poetry vs uv、Black vs Ruff vs flake8）。本模板在同类工具中只选择当前最优解，避免选择困难。

**2. 工具之间互相配合。** 例如：
- `uv` 的 `[dependency-groups]` 定义 dev 依赖（ruff、mypy、pytest、structlog）
- `pyproject.toml` 的 `[tool.ruff]` / `[tool.mypy]` / `[tool.pytest.ini_options]` 集中管理所有工具配置
- `check-constraints.py` 在每次写文件时检查是否违反了工具链规范
- `auto-gate.py` 在任务结束时自动运行 ruff + mypy + pytest

**3. 新项目零配置。** 本模板的检查机制（`check-scaffold.py`）会强制项目包含 `pyproject.toml`，并且提供了完整的模板。学生创建新项目时，Hook 会直接把包含所有工具配置的 `pyproject.toml` 模板输出到终端，复制粘贴即可起步。

**4. Hook 自动推行规范。** 学生不需要记住"用 pathlib 不要用 os.path"——只要代码中出现了 `os.path.join()`，Hook 就会拦截并告诉他改用 `pathlib`。规则通过自动化强制执行，而不是靠记忆和自觉。

---

## 快速安装

### 前置条件

- **Claude Code** 已安装
- **Python 3.12+**
- **uv**（Python 包管理器）：`curl -LsSf https://astral.sh/uv/install.sh | sh`

### 第一步：克隆本仓库

```bash
git clone git@github.com:leeing/python-cli-claude.git && cd python-cli-claude
```

### 第二步：项目级配置 → 复制到你的项目根目录

```bash
# 假设你的项目在 ~/my-cli-app
cp project/CLAUDE.md ~/my-cli-app/
cp -r project/.claude ~/my-cli-app/
```

> `.claude/settings.json` 会启用项目级 hooks。如果你已有同名文件，请手动合并 hooks 配置块，不要直接覆盖。

### 第三步：全局级配置 → 复制到 `~/.claude/`

```bash
# 全局 CLAUDE.md（追加合并，不要覆盖已有内容）
cat global/CLAUDE.md >> ~/.claude/CLAUDE.md

# Hooks 脚本
mkdir -p ~/.claude/hooks ~/.claude/skills
cp global/hooks/*.py ~/.claude/hooks/

# Skills
cp -r global/skills/hooks-setup ~/.claude/skills/

# ⚠️ settings.json 需手动合并，不能直接覆盖
# 方法一：用 Python 脚本合并（推荐）
python3 -c "
import json, os
settings_path = os.path.expanduser('~/.claude/settings.json')
with open(settings_path) as f:
    settings = json.load(f)
with open('global/settings.json') as f:
    hooks = json.load(f)
existing_hooks = settings.get('hooks', {})
for event_name, new_matchers in hooks.get('hooks', {}).items():
    existing_hooks.setdefault(event_name, [])
    existing_patterns = {m.get('matcher') for m in existing_hooks[event_name]}
    for matcher in new_matchers:
        if matcher.get('matcher') not in existing_patterns:
            existing_hooks[event_name].append(matcher)
settings['hooks'] = existing_hooks
with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')
print('✅ Global hooks merged into ~/.claude/settings.json')
"

# 方法二：手工合并 —— 打开 global/settings.json，
# 将其 hooks 对象复制到 ~/.claude/settings.json 的 hooks 字段中
```

---

## 仓库结构

```
python-cli-claude/
├── README.md
│
├── project/                             # ─┐ 复制到你的项目根目录
│   ├── CLAUDE.md                        #  │ Python CLI 技术栈规范
│   └── .claude/                         #  │
│       ├── settings.json                #  │ Hook 触发配置
│       ├── hooks/                       #  │
│       │   ├── _hook_utils.py           #  │ 共享工具函数
│       │   ├── check-constraints.py     #  │ 代码规范检查（PostToolUse）
│       │   ├── check-scaffold.py        #  │ 脚手架完整性检查
│       │   └── auto-gate.py             #  │ ★ 质量门禁（Stop）
│       └── skills/                      #  │
│           ├── acceptance/SKILL.md      #  │ 验收报告
│           ├── code-style/SKILL.md      #  │ 代码风格参考
│           ├── debugging/SKILL.md       #  │ 系统化调试
│           ├── hooks-setup/SKILL.md     #  │ Hooks 配置指南
│           └── new-feature/SKILL.md     #  │ 新建 CLI 功能流程
│                                        # ─┘
└── global/                              # ─┐ 复制到 ~/.claude/
    ├── CLAUDE.md                        #  │ 全局 AI 行为规范
    ├── settings.json                    #  │ 全局 Hook 配置（需合并）
    ├── hooks/                           #  │
    │   ├── README.md                    #  │ 安装说明
    │   ├── _path_safety.py              #  │ 路径安全检查
    │   ├── block-dangerous.py           #  │ 拦截危险命令
    │   ├── protect-files.py             #  │ 保护敏感文件
    │   ├── check-secrets.py             #  │ 检测硬编码凭证
    │   ├── check-type-suppression.py    #  │ type: ignore 数量限制
    │   └── log-commands.py              #  │ Bash 命令审计日志
    └── skills/                          #  │
        └── hooks-setup/SKILL.md         #  │ Hooks 配置指南
                                         # ─┘
```

---

## 设计原理

### 整体架构

本系统的核心思路是**分层约束 + 自动化验证**，通过三层机制协同工作：

```
┌──────────────────────────────────────────────────┐
│                   优先级                          │
│  SPEC.md > 项目 CLAUDE.md > 全局 CLAUDE.md > Skill │
├──────────────────────────────────────────────────┤
│                                                  │
│  CLAUDE.md (规则层)                               │
│  ├─ 全局: 通用行为准则 (Git 规范、安全通则)         │
│  └─ 项目: 技术栈专属规则 (uv/Ruff/Mypy 工具链)     │
│       │                                          │
│       ▼                                          │
│  Skills (流程层)                                  │
│  └─ 标准化工序: 新建功能 → 调试 → 验收              │
│       │                                          │
│       ▼                                          │
│  Hooks (执行层)                                   │
│  ├─ PreToolUse:  事前拦截 (危险命令、密钥检测)      │
│  ├─ PostToolUse: 事后检查 (代码规范、脚手架)        │
│  └─ Stop:        最终门禁 (lint/test 全量验证)      │
│                                                  │
└──────────────────────────────────────────────────┘
```

三者关系：

- **CLAUDE.md** 定义"应该怎么做"——AI 启动时加载为系统提示词，形成行为基线
- **Skills** 定义"具体怎么操作"——AI 遇到对应场景时自动加载，提供步骤化指导
- **Hooks** 强制"不许乱做"——在工具调用前后自动执行脚本，拦截违规行为并**附带修复指令**

关键设计决策：**Hook 不止于拦截，而是闭环**。每次拦截时 stderr 输出不仅是报错，还包含给 AI 看的修复指引。AI 读取 stderr → 理解问题 → 修复代码 → Hook 重新检查 → 通过。这个循环最多 3 轮，保证 AI 能自主纠错。

---

### CLAUDE.md —— AI 的行为准则

#### 为什么是 Markdown 而不是代码？

Claude Code 在启动时会将 `CLAUDE.md` 的内容注入到系统提示词（system prompt）中。这意味着**自然语言描述的规则比代码更有效**——AI 直接"读懂"规范，而不是被 API 拦截后才被动应对。

#### 两层 CLAUDE.md 的分工

| 文件 | 位置 | 内容性质 | 示例 |
|------|------|---------|------|
| 全局 `CLAUDE.md` | `~/.claude/CLAUDE.md` | 与技术栈无关的通用行为准则 | Git 工作流、安全通则、SPEC.md 协议、编码纪律 |
| 项目 `CLAUDE.md` | 项目根目录 | 技术栈专属规范 | uv/Ruff/Mypy 工具链、项目结构、禁止清单、Hook 恢复流程 |

冲突解决：**项目级覆盖全局级**。例如全局规范说"使用异步 IO"，项目规范可以进一步指定"使用 httpx + async"。

#### 自修复机制

项目 `CLAUDE.md` 第 4 节专门写了"Hook 失败恢复"流程：

1. 看到 `🚫 Auto Gate BLOCKED` 时不要停止
2. 阅读每个 `❌` 错误，定位问题
3. 修复后系统自动重新检查
4. 最多 3 轮自修复

这让 AI 遇到 Hook 拦截时知道该怎么办，而不是卡住或放弃。

---

### Skills —— AI 的操作手册

Skills 是存放在 `.claude/skills/<name>/SKILL.md` 中的 Markdown 文件，每个 Skill 定义了**一个标准化操作流程**。

#### Skill 的结构

```markdown
---
name: 系统化调试
description: 复现问题、定位根因、修复验证的调试流程
trigger: 当遇到 Bug、测试失败或异常行为时
---

## 流程
1. 复现问题（找到最小可复现用例）
2. 定位根因（二分法缩小范围）
3. 先写失败的测试
4. 修复代码
5. 运行 Auto Gate 验证
6. 报告结果
```

Claude Code 根据 `trigger` 字段判断何时激活 Skill。当用户说"test_export 失败了"，AI 自动匹配并加载 `debugging` Skill。

#### 本仓库包含的 Skills

| Skill | 层级 | 触发场景 |
|-------|------|---------|
| `new-feature` | 项目 | 用户要求添加 CLI 命令/子命令/选项 |
| `code-style` | 项目 | AI 需要确认编码规范时 |
| `debugging` | 项目 | 遇到 Bug 或测试失败 |
| `acceptance` | 项目 | 功能开发完成，准备报告 |
| `hooks-setup` | 项目+全局 | 需要配置或调试 hooks |

#### 为什么用 Skill 而不是全写在 CLAUDE.md？

- **按需加载**：Skill 只有触发时才注入上下文，避免 CLAUDE.md 过长
- **可组合**：同一个 Skill 可以被不同项目复用
- **专业化**：每个 Skill 聚焦一个场景，写得非常详细

---

### Hooks —— 自动化质量门禁

Hooks 是 Claude Code 最核心的自动化机制。它们是在**工具调用前后**自动执行的 Python 脚本，通过 `settings.json` 配置触发规则。

#### Hook 执行模型

```
用户输入 → AI 决策调用工具
              │
              ▼
         PreToolUse Hooks      ← 全局 hooks 在此拦截
         (exit 2 = 阻止调用)
              │
              ▼
         工具实际执行            ← Write / Edit / Bash
              │
              ▼
         PostToolUse Hooks     ← 项目 hooks 在此检查
         (exit 2 = 阻止提交)
              │
              ▼
         AI 收到结果，继续工作
              │
              ▼
         Stop Hook             ← Auto Gate 最终门禁
         (exit 2 = 任务未完成)
```

#### 三层 Hooks 的分工

| 层级 | 时机 | 职责 | 失败后果 |
|------|------|------|---------|
| 全局 PreToolUse | 工具执行前 | 安全底线（危险命令、密钥、文件保护） | 阻止工具调用 |
| 项目 PostToolUse | 文件写入后 | 代码规范（类型标注、print 调试、os.path 等） | 阻止文件写入 |
| 项目 Stop | Agent 停止时 | 质量门禁（ruff、mypy、pytest） | 标记任务未完成 |

#### Exit Code 约定

| 退出码 | 含义 | AI 的行为 |
|--------|------|----------|
| **0** | 通过 | 继续执行 |
| **1** | 非致命错误 | 继续执行（警告级别） |
| **2** | 拦截 | **阻止操作**，stderr 内容会显示给 AI 作为修复指令 |

Exit 2 是整个机制的关键——它不仅阻止了违规操作，还通过 stderr **告诉 AI 为什么被拦截以及如何修复**，形成自动纠错闭环。

#### Hook 配置 (`settings.json`)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",   // 匹配这些工具
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/check-constraints.py",
            "timeout": 15                      // 超时保护
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",                         // 空 = 每次都触发
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/auto-gate.py",
            "timeout": 300
          }
        ]
      }
    ]
  }
}
```

`matcher` 支持 `|` 分隔匹配多个工具名；`Stop` 事件下 `matcher` 为空表示 Agent 每次停止都触发。

---

### Auto Gate 详解

Auto Gate 是整个系统最关键的 Hook，有必要单独讲解。

#### 它解决什么问题？

AI 编程的核心痛点：**AI 声称"完成了"，但代码实际上跑不通**——import 错误、类型不匹配、测试失败。Auto Gate 在 AI 每次"交作业"时强制执行质量检查，**不过关就不算完成**。

#### 触发时机

Auto Gate 是 **Stop Hook**，在 Claude Code Agent **完成任务、准备停止时**触发。这意味着：

- **不是每次编辑都跑**（不会干扰写代码的流畅度）
- **不在 AI 思考/搜索时跑**（不浪费上下文窗口）
- **恰好在 AI 说"我做好了"的那一刻**执行验证

#### 执行流程

```
Agent 完成工作，准备停止
        │
        ▼
  git diff HEAD --name-only    ← 找出变更的 .py 文件
        │
        ├─ 无变更 → SKIP（跳过）
        │
        ▼
  ┌─ 并行执行 ─────────────────────┐
  │  ruff format --check    ← 格式检查
  │  ruff check             ← Lint 检查
  │  mypy (仅 src/ 文件)     ← 类型检查
  └────────────────────────────────┘
        │
        ▼
  pytest (智能匹配)           ← 只跑相关测试
  ├─ 变更 tests/test_foo.py → 直接跑
  ├─ 变更 src/foo.py        → 找 tests/test_foo.py
  └─ 找不到匹配测试          → 跳过
        │
        ▼
  ┌─ 全部通过 → exit 0 → ✅ Auto Gate passed
  └─ 任一失败 → exit 2 → 🚫 Auto Gate BLOCKED
                         stderr 输出修复指引
```

#### 设计亮点

**1. 增量检查（只查变更文件）**

传统 CI 跑全量，但 Auto Gate 通过 `git diff --name-only HEAD` 只检查本次会话修改的文件。一个项目 500 个文件，你只改了 3 个，Auto Gate 就只查这 3 个。几十毫秒完成，不影响体验。

**2. 并行执行**

ruff-format、ruff-check、mypy 三个检查通过 `ThreadPoolExecutor` 并行跑，而不是串行排队。三个检查中最慢的决定总耗时。

**3. 智能测试匹配**

不是跑全部测试，而是根据变更文件推断需要跑的测试：

```
src/cli/export.py  → tests/test_export.py
src/models/user.py → tests/test_user.py
tests/test_auth.py  → 直接跑（本身就是测试文件）
```

找不到匹配的测试文件时**跳过 pytest**（不报错），避免因项目初期测试覆盖不全而卡死。

**4. 超时保护**

每个检查都有 timeout 保护：
- `settings.json` 中 auto-gate 整体 timeout = 300 秒
- pytest 额外 60 秒硬超时，防止挂起的测试卡死流程

**5. 可操作的回显**

Auto Gate 失败时的 stderr 不是冷冰冰的报错，而是**给 AI 看的分步指令**：

```
🚫 Auto Gate BLOCKED. Failures: ruff-check, mypy

=== INSTRUCTIONS FOR AI AGENT ===
DO NOT STOP. You MUST fix the errors above and try again.
Step 1: Read each ❌ error message above carefully.
Step 2: Fix the code that caused each failure.
Step 3: After fixing, the gate will re-run automatically.
=================================
```

AI 读到这段文字就知道：不能停、读错误、修复、重来。

**6. 3 轮自修复上限**

CLAUDE.md 规定最多 3 轮自修复。超过 3 轮仍然不过，AI 必须向用户报告现状。这防止了 AI 陷入无限修复循环（例如两个 lint 规则相互矛盾的情况）。

#### 完整生命周期示例

```
用户: "帮我添加一个 export 命令"

AI: 创建 src/cli/export.py, tests/test_export.py
    → PostToolUse: check-constraints ✅ (没有 print、os.path 等问题)
    → PostToolUse: check-scaffold ✅ (pyproject.toml 已存在)

AI: "我做完了"

    → Stop: auto-gate 启动
    → ruff-format ✅
    → ruff-check ❌ (F401: unused import)
    → mypy ✅
    → pytest ❌ (test_export_format: AssertionError)

AI 看到: 🚫 Auto Gate BLOCKED
    读错误 → 删除未使用的 import → 修复测试断言
    (第 1 轮自修复)

    → Stop: auto-gate 重新启动
    → ruff-format ✅
    → ruff-check ✅
    → mypy ✅
    → pytest ✅

    ✅ Auto Gate passed (3 file(s) checked)

AI: "export 命令已完成，所有检查通过。"
```

这整个流程**无需用户干预**。用户只需在最后看到结果。

---

## Hooks 参考

### 项目级 Hooks

| Hook | 触发时机 | 检查内容 |
|------|---------|---------|
| `check-constraints.py` | 每次写入 .py 文件后 | 11 项检查：type:ignore 数量、noqa 豁免安全规则、os.path、os.environ、print()、文件行数、time.sleep、requests、泛型 except Exception、旧式类型标注 (Optional/Union/List/Dict)、assert 语句 |
| `check-scaffold.py` | 每次写入 .py 文件后 | 确保 pyproject.toml、src/ 目录、至少一个 test_*.py 存在 |
| `auto-gate.py` | Agent 停止时 | ruff format --check + ruff check + mypy + pytest（仅变更文件） |

### 全局 Hooks

| Hook | 触发时机 | 功能 |
|------|---------|------|
| `block-dangerous.py` | Bash 执行前 | 拦截 `rm -rf /`、fork bomb、`curl\|sh`、push/merge/rebase main |
| `protect-files.py` | 写文件 / Bash 前 | 保护 `.env`、SSH 密钥、`/etc/`、全局 `settings.json` |
| `check-secrets.py` | 写文件前 | 检测硬编码凭证（密码/token/私钥/AWS key） |
| `check-type-suppression.py` | 写文件后 | 单文件 `# type: ignore` 超过 3 处时拦截 |
| `log-commands.py` | Bash 执行后 | 所有命令写入审计日志 `~/.claude/hooks-logs/` |

### Exit Code 约定

| 退出码 | 含义 | AI 的行为 |
|--------|------|----------|
| 0 | 通过 | 继续执行 |
| 1 | 非致命错误 | 继续执行 |
| 2 | 拦截 | 阻止操作，stderr 作为修复指引显示给 AI |

---

## Skills 参考

### 项目级 Skills

| Skill | 用途 |
|-------|------|
| `new-feature` | 为 CLI 添加新命令/子命令的标准流程：SPEC.md → 参数设计 → 实现 → 测试 |
| `code-style` | Python CLI 类型标注、structlog 日志、pydantic-settings 配置的编码规范示例 |
| `debugging` | 系统化调试流程：复现 → 二分定位 → 写失败测试 → 修复 → Auto Gate 验证 |
| `acceptance` | 功能完成后运行 Auto Gate，输出标准化验收报告（含 pass/fail 数量和覆盖率） |
| `hooks-setup` | Hooks 架构详解、跨平台配置、调试方法、自定义 hook 编写教程 |

### 全局 Skills

| Skill | 用途 |
|-------|------|
| `hooks-setup` | Hooks 配置与开发完全指南 |

---

## 使用示例

安装完成后，在 Claude Code 中：

```
# 新建功能
> 帮我添加一个 export 命令，支持 --format json|csv

# 调试问题
> test_export 失败了，帮我调试

# 验收
> 功能完成了，帮我生成验收报告
```

Claude 会：
1. 遵循 CLAUDE.md 中的技术栈规范（用 uv 管理依赖、pathlib 处理路径、structlog 打日志）
2. 匹配并加载对应的 Skill（new-feature → debugging → acceptance）
3. 每次写文件后 hooks 自动检查代码规范
4. 任务完成时 Auto Gate 强制运行 ruff + mypy + pytest，不通过不算完成

---

## 常见问题

### Q: 如何禁用某个 hook？

编辑对应层级的 `settings.json`，删除对应的 matcher 配置块。例如禁用项目级脚手架检查：

```json
// 删除这个配置块即可
{
  "matcher": "Write|Edit|MultiEdit",
  "hooks": [
    {
      "type": "command",
      "command": "python3 .claude/hooks/check-scaffold.py"
    }
  ]
}
```

### Q: Hook 报错如何修复？

阅读 `❌` 错误信息 → 根据提示修改代码 → 系统自动重新检查。AI 最多进行 3 轮自修复。

### Q: 全局和项目级 settings.json 冲突怎么办？

两个文件独立工作，不冲突。**全局 hooks 先执行**（PreToolUse），如果拦截（exit 2）则后续 hooks 和工具调用均不执行。

### Q: 为什么 check-scaffold 一直报错？

这说明你的项目缺少 `pyproject.toml`、`src/` 目录或 `tests/test_*.py`。这是脚手架完整性检查，确保项目有最基本的工程结构。按照 stderr 中输出的模板创建缺失文件即可。

### Q: pytest 超时怎么办？

Auto Gate 对 pytest 有 60 秒硬超时。如果测试太慢，考虑：
- 检查是否有 `time.sleep` 或同步阻塞 IO
- 将集成测试和单元测试分开
- 在 auto-gate.py 中调整 timeout 值

---

## 许可

本仓库仅包含规范模板文件，无运行时依赖。源自 [claude-rules](https://github.com/anthropics/claude-rules) 项目。
