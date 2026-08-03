#!/bin/bash
# prjm-gate.sh —— 编码前置闸门 hook（PreToolUse, 匹配 Write|Edit）
# 作用：任何"代码文件"的写入/编辑之前，检查是否已过 prjm 路由（存在新鲜的标记文件）。
#       未路由 → exit 2 拦截；已路由 → exit 0 放行。
# 依赖：jq（用于从 stdin JSON 解析 file_path）

# --- jq 定位：优先 PATH，其次 winget Links 目录（Windows 安装后 PATH 可能未刷新）---
JQ="jq"
if ! command -v jq >/dev/null 2>&1; then
  WINGET_JQ="$LOCALAPPDATA/Microsoft/WinGet/Links/jq.exe"
  if [ -x "$WINGET_JQ" ]; then
    JQ="$WINGET_JQ"
  fi
fi

input=$(cat)
file_path=$(printf '%s' "$input" | "$JQ" -r '.tool_input.file_path // empty' 2>/dev/null)

# 解析不到路径 → 不拦截，放行（避免误伤非文件类工具）
if [ -z "$file_path" ]; then
  exit 0
fi

# --- 放行清单：非代码文件 / 状态目录 / 产出目录 / hook 自身，一律放行 ---
case "$file_path" in
  *.md|*.markdown|*.json|*.txt|*.log|*.yaml|*.yml|*.toml|*.ini|*.csv) exit 0 ;;
  */.ai/*|*/output/*|*/.qoder/*) exit 0 ;;
esac

# --- 拦截清单：只对代码文件生效 ---
case "$file_path" in
  *.js|*.jsx|*.ts|*.tsx|*.vue|*.mjs|*.cjs|\
  *.py|*.java|*.go|*.rs|*.rb|*.php|\
  *.c|*.h|*.cpp|*.hpp|*.cc|*.cs|*.kt|*.swift|*.scala|\
  *.sql|*.sh)
    ;;
  *)
    # 其他未知类型：放行（最小可用版本只管代码文件）
    exit 0 ;;
esac

# --- 核验路由标记：项目根下 .ai/.prjm-gate，30 分钟内有效 ---
cwd=$(printf '%s' "$input" | "$JQ" -r '.cwd // empty' 2>/dev/null)
GATE_FILE="$cwd/.ai/.prjm-gate"

# --- 遥测：代码文件的每次判定落盘到 .ai/telemetry/gate.log（客观使用痕迹，供减脂复盘）---
log_verdict() {
  if [ -n "$cwd" ] && [ -d "$cwd/.ai" ]; then
    mkdir -p "$cwd/.ai/telemetry" 2>/dev/null
    echo "$(date '+%Y-%m-%dT%H:%M:%S') $1 $file_path" >> "$cwd/.ai/telemetry/gate.log" 2>/dev/null
  fi
}

if [ ! -f "$GATE_FILE" ]; then
  log_verdict "BLOCK-nogate"
  echo "【编码前置闸门】未检测到 prjm 路由标记（$GATE_FILE 不存在）。" >&2
  echo "任何代码修改前必须先经 prjm 路由：判定技能→加载技能→影响分析→用户确认，通过后写入标记文件再编码。" >&2
  echo "本次对 [$file_path] 的编辑已被拦截（Rule §1.1 编码前置闸门）。" >&2
  exit 2
fi

# 标记新鲜度：文件修改时间距今是否超过 1800 秒（30 分钟）
now=$(date +%s)
mtime=$(date -r "$GATE_FILE" +%s 2>/dev/null || echo 0)
age=$((now - mtime))
if [ "$age" -gt 1800 ]; then
  log_verdict "BLOCK-expired(${age}s)"
  echo "【编码前置闸门】prjm 路由标记已过期（${age}s > 1800s）。请重新走 prjm 路由确认后再编码。" >&2
  echo "本次对 [$file_path] 的编辑已被拦截（Rule §1.1）。" >&2
  exit 2
fi

# 通过
log_verdict "PASS"
exit 0
