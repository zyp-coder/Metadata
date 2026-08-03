"""技术函数插件（自定义公式函数注册入口）。

当内置32个业务函数不满足需求时，技术人员在本文件中用 @register_function
装饰器注册 Python 函数，即可自动纳入以下全链路（无需改任何其他代码）：
- 表达式语法校验 / 参数个数校验（formula_engine.validate_expression）
- 求值执行（formula_engine._eval_func）
- 前端公式编辑器函数库「技术函数」分类（get_available_functions）
- AI 自然语言生成表达式的可用函数清单（ai_service.generate_formula）

注册规范：
1. 函数名全大写，Excel 风格，建议动宾结构（如 PAD_LEFT / REGEX_EXTRACT）
2. category 固定为 '技术函数'
3. description 必须写清签名与用途：'NAME(参数1, [可选参数]) — 用途说明'
4. 函数签名固定为 (args: list, ctx: dict)，args 为已求值的参数列表
5. 业务性错误抛 FormulaRuntimeError（会被 IFERROR 捕获并友好提示）

本文件由 formula_engine.py 末尾自动导入，新增函数保存后重启服务即生效。
"""
import hashlib
import re

from .formula_engine import FormulaRuntimeError, register_function


@register_function('PAD_LEFT', 2, 3, 'PAD_LEFT(文本, 长度, [填充字符]) — 左侧补齐到指定长度，默认补0', category='技术函数')
def func_pad_left(args, ctx):
    text = '' if args[0] is None else str(args[0])
    try:
        width = int(float(args[1]))
    except (ValueError, TypeError):
        raise FormulaRuntimeError(f"PAD_LEFT长度参数无效: {args[1]}")
    fill = str(args[2])[0] if len(args) > 2 and str(args[2]) else '0'
    return text.rjust(width, fill)


@register_function('REGEX_EXTRACT', 2, 3, 'REGEX_EXTRACT(文本, 正则, [组序号]) — 正则提取首个匹配，未匹配返回空', category='技术函数')
def func_regex_extract(args, ctx):
    text = '' if args[0] is None else str(args[0])
    pattern = str(args[1])
    group = int(float(args[2])) if len(args) > 2 else 0
    try:
        m = re.search(pattern, text)
    except re.error as e:
        raise FormulaRuntimeError(f"REGEX_EXTRACT正则无效: {e}")
    if not m:
        return ''
    try:
        return m.group(group) or ''
    except IndexError:
        raise FormulaRuntimeError(f"REGEX_EXTRACT组序号超出范围: {group}")


@register_function('REGEX_REPLACE', 3, 3, 'REGEX_REPLACE(文本, 正则, 替换文本) — 正则替换全部匹配', category='技术函数')
def func_regex_replace(args, ctx):
    text = '' if args[0] is None else str(args[0])
    try:
        return re.sub(str(args[1]), str(args[2]), text)
    except re.error as e:
        raise FormulaRuntimeError(f"REGEX_REPLACE正则无效: {e}")


@register_function('SPLIT_INDEX', 3, 3, 'SPLIT_INDEX(文本, 分隔符, 序号) — 按分隔符拆分后取第N段（从1开始），越界返回空', category='技术函数')
def func_split_index(args, ctx):
    text = '' if args[0] is None else str(args[0])
    sep = str(args[1])
    if not sep:
        raise FormulaRuntimeError('SPLIT_INDEX分隔符不能为空')
    try:
        idx = int(float(args[2]))
    except (ValueError, TypeError):
        raise FormulaRuntimeError(f"SPLIT_INDEX序号无效: {args[2]}")
    parts = text.split(sep)
    if 1 <= idx <= len(parts):
        return parts[idx - 1]
    return ''


@register_function('MAP_VALUE', 2, 3, 'MAP_VALUE(值, "旧1:新1;旧2:新2", [默认值]) — 按映射表转换，未命中返回默认值或原值', category='技术函数')
def func_map_value(args, ctx):
    val = '' if args[0] is None else str(args[0])
    mapping_str = str(args[1])
    mapping = {}
    for pair in mapping_str.split(';'):
        pair = pair.strip()
        if not pair:
            continue
        if ':' not in pair:
            raise FormulaRuntimeError(f"MAP_VALUE映射项格式错误（应为 旧值:新值）: {pair}")
        k, v = pair.split(':', 1)
        mapping[k.strip()] = v.strip()
    if val in mapping:
        return mapping[val]
    return str(args[2]) if len(args) > 2 else val


@register_function('HASH_MD5', 1, 2, 'HASH_MD5(文本, [长度]) — 生成MD5摘要（小写16进制），可截取前N位，常用于迁移对账', category='技术函数')
def func_hash_md5(args, ctx):
    text = '' if args[0] is None else str(args[0])
    digest = hashlib.md5(text.encode('utf-8')).hexdigest()
    if len(args) > 1:
        try:
            n = int(float(args[1]))
        except (ValueError, TypeError):
            raise FormulaRuntimeError(f"HASH_MD5长度参数无效: {args[1]}")
        if n > 0:
            return digest[:n]
    return digest
