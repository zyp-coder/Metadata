/**
 * 计算表达式格式化（代码编辑器风格）：
 * 函数名大写化 + 补全缺失右括号 + 长函数调用换行缩进（每个参数独立一行，两空格缩进）。
 * 保护字段引用 {...} 和字符串字面量 "..." 不被误改。
 * 供 FormulaEditor（手动格式化/AI 生成后自动格式化）与 TrialCalculation（表达式展示）复用。
 */
export function formatExpressionText(raw: string): string {
  // 1. 抽离字段引用和字符串字面量，用占位符保护（占位符内无括号/逗号，后续处理安全）
  const placeholders: string[] = []
  const protectedExpr = raw
    .replace(/\{[^}]*\}/g, (m) => {
      placeholders.push(m)
      return `\x00${placeholders.length - 1}\x00`
    })
    .replace(/"[^"]*"/g, (m) => {
      placeholders.push(m)
      return `\x00${placeholders.length - 1}\x00`
    })

  // 2. 压扁为单行：去掉已有换行/缩进，函数名大写化，逗号后统一 ', '
  let compact = protectedExpr.replace(/\s+/g, ' ').trim()
  compact = compact.replace(/\b([A-Za-z_][A-Za-z0-9_]*)\s*\(/g, (_, name) => `${name.toUpperCase()}(`)
  compact = compact.replace(/\s*,\s*/g, ', ')

  // 3. 补全缺失的右括号（栈匹配）
  let depth = 0
  for (const ch of compact) {
    if (ch === '(') depth++
    else if (ch === ')') depth--
  }
  if (depth > 0) compact += ')'.repeat(depth)

  // 4. 计算每个字符的「展示宽度」前缀和（占位符按还原后真实长度计），用于判断括号内容是否超长
  const weights: number[] = new Array(compact.length).fill(1)
  const phRe = /\x00(\d+)\x00/g
  let phm: RegExpExecArray | null
  while ((phm = phRe.exec(compact)) !== null) {
    const realLen = placeholders[Number(phm[1])].length
    weights[phm.index] = realLen
    for (let k = phm.index + 1; k < phm.index + phm[0].length; k++) weights[k] = 0
  }
  const prefix: number[] = new Array(compact.length + 1).fill(0)
  for (let k = 0; k < compact.length; k++) prefix[k + 1] = prefix[k] + weights[k]

  // 5. 匹配括号对，内容展示宽度超过阈值的括号标记为「换行展开」
  const BREAK_THRESHOLD = 40
  const openStack: number[] = []
  const breakParen = new Set<number>()
  for (let k = 0; k < compact.length; k++) {
    if (compact[k] === '(') openStack.push(k)
    else if (compact[k] === ')') {
      const open = openStack.pop()
      if (open !== undefined && prefix[k] - prefix[open + 1] > BREAK_THRESHOLD) breakParen.add(open)
    }
  }

  // 6. 输出：展开的括号后换行缩进，其内顶层逗号后换行，闭括号回退缩进独立成行
  const INDENT = '  '
  let out = ''
  let level = 0
  const brokenStack: boolean[] = []
  for (let k = 0; k < compact.length; k++) {
    const ch = compact[k]
    if (ch === '(') {
      const broken = breakParen.has(k)
      brokenStack.push(broken)
      if (broken) {
        level++
        out += '(\n' + INDENT.repeat(level)
        while (compact[k + 1] === ' ') k++
      } else {
        out += '('
      }
    } else if (ch === ')') {
      const broken = brokenStack.pop()
      if (broken) {
        level--
        out += '\n' + INDENT.repeat(level) + ')'
      } else {
        out += ')'
      }
    } else if (ch === ',' && brokenStack[brokenStack.length - 1]) {
      out += ',\n' + INDENT.repeat(level)
      while (compact[k + 1] === ' ') k++
    } else {
      out += ch
    }
  }

  // 7. 还原占位符
  out = out.replace(/\x00(\d+)\x00/g, (_, idx) => placeholders[Number(idx)])

  return out
}
