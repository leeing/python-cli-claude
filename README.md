# Python CLI — Claude Code 规范模板

> 适用于 **Claude Code** 的 Python CLI 项目规范模板，包含 AI 行为规则、自动化质量门禁（Hooks）和操作技能（Skills）。

## 这是什么？

本仓库提供了一套可直接复用的 Claude Code 配置，帮助学生快速在自己的 Python CLI 项目中建立：

- **AI 行为规范**（CLAUDE.md）—— 告诉 Claude 用什么工具链、遵循什么编码规范
- **自动化质量门禁**（Hooks）—— 自动拦截不合规代码、运行 lint/test
- **操作技能指南**（Skills）—— 标准化流程（新建功能、调试、验收）

分为两个层级：

| 层级 | 目录 | 安装位置 | 作用范围 |
|------|------|---------|---------|
| **项目级** | `project/` | 你的项目根目录 | 当前项目 |
| **全局级** | `global/` | `~/.claude/` | 所有项目 |

**优先级**：`SPEC.md > 项目级 CLAUDE.md > 全局 CLAUDE.md > Skill`

---

## 前置条件

- **Claude Code** 已安装
- **Python 3.12+**
- **uv**（Python 包管理器）：`curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## 安装（3 步手工）

### 第一步：克隆本仓库

```bash
git clone <repo-url> && cd python-cli
```

### 第二步：项目级配置 → 复制到你的项目根目录

```bash
# 假设你的项目在 ~/my-cli-app
cp project/CLAUDE.md ~/my-cli-app/
cp -r project/.claude ~/my-cli-app/
```

> `.claude/settings.json` 会启用项目级 hooks（check-constraints、check-scaffold、auto-gate）。
> 如果你已有 `.claude/settings.json`，请手动合并 hooks 部分，不要直接覆盖。

### 第三步：全局级配置 → 复制到 `~/.claude/`

```bash
# 复制全局 CLAUDE.md（和已有内容合并，不要覆盖）
cat global/CLAUDE.md >> ~/.claude/CLAUDE.md

# 复制 hooks 脚本
mkdir -p ~/.claude/hooks ~/.claude/skills
cp global/hooks/*.py ~/.claude/hooks/

# 复制 skills
cp -r global/skills/hooks-setup ~/.claude/skills/

# ⚠️ 合并 settings.json（不要直接覆盖！）
# 打开 global/settings.json，将其中的 hooks 配置合并到 ~/.claude/settings.json
# 详见 global/hooks/README.md 中的合并脚本
```

> 全局 hooks 提供安全底线：危险命令拦截、密钥检测、文件保护等，对所有项目生效。

---

## 仓库结构

```
python-cli/
├── README.md
│
├── project/                             # ─┐ 复制到你的项目根目录
│   ├── CLAUDE.md                        #  │ Python CLI 技术栈规范
│   └── .claude/                         #  │
│       ├── settings.json                #  │ Hook 配置
│       ├── hooks/                       #  │
│       │   ├── _hook_utils.py           #  │ 共享工具函数
│       │   ├── check-constraints.py     #  │ 代码规范检查（PostToolUse）
│       │   ├── check-scaffold.py        #  │ 脚手架完整性检查
│       │   └── auto-gate.py             #  │ 质量门禁（Stop）
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
    │   └── log-commands.py              #  │ Bash 命令日志
    └── skills/                          #  │
        └── hooks-setup/SKILL.md         #  │ Hooks 配置指南
                                         # ─┘
```

---

## Hooks 参考

### 项目级 Hooks

| Hook | 触发时机 | 功能 |
|------|---------|------|
| `check-constraints.py` | 写 .py 文件后 | 检查 type:ignore 数量、noqa 豁免、os.path、print、os.environ、文件大小、time.sleep、requests、泛型异常、旧式类型标注、assert 等 |
| `check-scaffold.py` | 写 .py 文件后 | 确保 pyproject.toml、src/、tests/ 存在 |
| `auto-gate.py` | Agent 停止时 | 对变更文件运行 ruff format、ruff check、mypy、pytest |

### 全局 Hooks

| Hook | 触发时机 | 功能 |
|------|---------|------|
| `block-dangerous.py` | Bash 执行前 | 拦截 `rm -rf /`、fork bomb、`curl\|sh`、强制 push/merge/rebase main 等 |
| `protect-files.py` | 写文件/Bash 前 | 保护 `.env`、SSH 密钥、`/etc/`、全局 settings.json 不被修改 |
| `check-secrets.py` | 写文件前 | 检测硬编码凭证（密码/token/私钥/AWS key） |
| `check-type-suppression.py` | 写文件后 | 单文件 `# type: ignore` 超过 3 处时拦截 |
| `log-commands.py` | Bash 执行后 | 所有命令写入日志 `~/.claude/hooks-logs/` |

### Exit Code 约定

| 退出码 | 含义 |
|--------|------|
| 0 | 通过，继续执行 |
| 1 | 非致命错误，继续执行 |
| 2 | 拦截，阻止操作，stderr 显示给 AI |

---

## Skills 参考

### 项目级 Skills

| Skill | 用途 |
|-------|------|
| `new-feature` | 为 CLI 添加新命令/子命令的标准流程 |
| `code-style` | Python CLI 类型标注、日志、配置编码规范示例 |
| `debugging` | 系统化调试：复现 → 定位根因 → 修复验证 |
| `acceptance` | 功能完成后运行 Auto Gate 并输出标准化验收报告 |
| `hooks-setup` | Hooks 架构理解、跨平台配置、调试、自定义编写 |

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

Claude 会自动遵循 CLAUDE.md 规范、触发相应 Skill，每次写文件后 hooks 会自动检查代码质量。

---

## 常见问题

### Q: 如何禁用某个 hook？

编辑 `.claude/settings.json` 或 `~/.claude/settings.json`，删除对应的 matcher 配置块。

### Q: Hook 报错如何修复？

阅读 `❌` 错误信息 → 根据提示修改代码 → 系统自动重新检查。最多 3 轮自修复。

### Q: 全局和项目级 settings.json 冲突怎么办？

两个文件独立工作，不冲突。全局 hooks 先执行，如果拦截则后续都不执行。

---

## 许可

本仓库仅包含规范模板文件，无运行时依赖。源自 [claude-rules](https://github.com/anthropics/claude-rules) 项目。
