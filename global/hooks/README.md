# Global Hooks (全局安全防线)

> 这些 hooks 可部署到 `~/.claude/settings.json` 或 `~/.codex/config.toml`，对所有项目生效。
> 与项目级 hooks（如 `python-stdlib/hooks/`）互不冲突，分层执行。

## 安装

```bash
# 1. 复制脚本到全局 hooks 目录
mkdir -p ~/.claude/hooks ~/.claude/hooks-logs
for hook in block-dangerous.py log-commands.py protect-files.py check-secrets.py check-type-suppression.py; do
  cp "rules/global/hooks/$hook" ~/.claude/hooks/
done
chmod +x ~/.claude/hooks/*.py

# 2. 将 settings.claude.json 中的 hooks 配置合并到 ~/.claude/settings.json
# 不要直接覆盖；现实现按 event + matcher 级别追加，保留现有 env/model 等配置
python3 -c "
import json, os
settings_path = os.path.expanduser('~/.claude/settings.json')
with open(settings_path) as f:
    settings = json.load(f)
with open('rules/global/hooks/settings.claude.json') as f:
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
print('✅ Claude hooks merged into global settings')
"

# 3. 重启 Claude Code
```

Codex CLI 由 `init.py` 自动复制同一批脚本到 `~/.codex/hooks/`，并把 hooks 配置追加到 `~/.codex/config.toml` 的 claude-rules 管理区块中。Codex hooks 需要：

```toml
[features]
hooks = true
```

`init.py` 只会为本次 `--tools` 选择的工具安装对应全局 hooks；例如 `--tools opencode` 不会修改 `~/.claude` 或 `~/.codex`。

如果用户已经存在 legacy `~/.codex/hooks.json`，`init.py` 会跳过写入全局 `~/.codex/config.toml` 的 claude-rules hook 区块，避免两套 Codex 全局 hook 配置互相覆盖。

## Hooks 说明

| 脚本 | 阶段 | 触发条件 | 功能 |
|------|------|---------|------|
| `block-dangerous.py` | PreToolUse | Bash | 拦截 `rm -rf /`、fork bomb、`curl|sh`、push/merge/rebase main 等高风险命令 |
| `log-commands.py` | PostToolUse | Bash | 所有 bash 命令写入 `~/.claude/hooks-logs/commands-YYYY-MM-DD.log` |
| `protect-files.py` | PreToolUse | Bash|Edit|Write|MultiEdit | 保护 `.env`、SSH 密钥、`/etc/`、全局 `settings.json` 不被修改 |
| `check-secrets.py` | PreToolUse | Edit|Write|MultiEdit | 检测写入文件中的硬编码凭证（密码/token/私钥/AWS key） |
| `check-type-suppression.py` | PostToolUse | Edit|Write|MultiEdit | 单文件 type-suppress 注释超过 3 处时拦截，强制重构 |

## 与项目级 hooks 的关系

```text
~/.claude/settings.json 或 ~/.codex/config.toml (全局)
  └── 安全底线：block-dangerous + protect-files + check-secrets + check-type-suppression + log-commands

项目根 .claude/settings.json 或 .codex/config.toml (项目级)
  └── check-constraints + check-scaffold + auto-gate
```

全局 hooks 先执行（PreToolUse），如果拦截（exit 2）则后续 hooks 和工具调用均不执行。

## 自定义

- **block-dangerous.py**: 修改 `DANGEROUS_PATTERNS` 列表增减规则
- **protect-files.py**: 修改 `PROTECTED_BASENAMES` / `PROTECTED_PREFIXES` 增减保护文件
- **log-commands.py**: 日志默认存 `~/.claude/hooks-logs/`，修改 `LOG_DIR` 可更改路径

## Exit Code 约定

| 退出码 | 含义 | 效果 |
|--------|------|------|
| 0 | 通过 | 继续执行 |
| 1 | 错误 | 非致命，继续执行 |
| 2 | 拦截 | 阻止工具调用，stderr 内容显示给模型 |
