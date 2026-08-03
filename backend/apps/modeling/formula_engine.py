"""
公式引擎核心 — Excel风格表达式解析器 + 函数库 + 求值器。

架构：
    表达式字符串 → tokenize() → Token流 → parse() → AST → evaluate(context) → 结果

字段引用语法: {表名.字段名}
函数调用语法: FUNC_NAME(arg1, arg2, ...)
运算符: +, -, *, /, >, <, >=, <=, =, <>, &(文本拼接)
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Any
from datetime import date, datetime

# ============================================================
# 错误类型
# ============================================================


class FormulaError(Exception):
    """公式引擎基类异常。"""
    pass


class FormulaSyntaxError(FormulaError):
    """语法错误。"""
    def __init__(self, message: str, position: int = -1):
        self.position = position
        super().__init__(f"语法错误(位置{position}): {message}" if position >= 0 else f"语法错误: {message}")


class FormulaReferenceError(FormulaError):
    """字段引用错误。"""
    def __init__(self, ref_name: str):
        self.ref_name = ref_name
        super().__init__(f"字段引用未找到: {ref_name}")


class FormulaRuntimeError(FormulaError):
    """运行时错误（除零、类型不匹配等）。"""
    pass


class CircularDependencyError(FormulaError):
    """循环依赖错误。"""
    def __init__(self, cycle_path: list):
        self.cycle_path = cycle_path
        super().__init__(f"检测到循环依赖: {' → '.join(cycle_path)}")


# ============================================================
# 引用解析
# ============================================================

REF_PATTERN = re.compile(r'\{([^.}]+)\.([^}]+)\}')


def extract_references(expression: str) -> list[dict]:
    """从表达式中提取字段引用。返回 [{"table_name":"xxx","field_code":"xxx"}]"""
    return [{"table_name": m[0], "field_code": m[1]} for m in REF_PATTERN.findall(expression)]


# ============================================================
# Token 定义
# ============================================================


class TokenType(Enum):
    NUMBER = 'NUMBER'
    STRING = 'STRING'
    BOOL = 'BOOL'
    REF = 'REF'           # {表名.字段名}
    FUNC = 'FUNC'         # 函数名
    COMMA = 'COMMA'
    LPAREN = 'LPAREN'
    RPAREN = 'RPAREN'
    OPERATOR = 'OPERATOR'  # +,-,*,/,>,<,>=,<=,=,<>,&
    EOF = 'EOF'


@dataclass
class Token:
    type: TokenType
    value: Any
    position: int = 0


# ============================================================
# 词法分析器 (Tokenizer)
# ============================================================

# 运算符（按长度降序匹配）
OPERATORS = ['>=', '<=', '<>', '+', '-', '*', '/', '>', '<', '=', '&']


def tokenize(expression: str) -> list[Token]:
    """将表达式字符串分割为 Token 流。"""
    tokens = []
    i = 0
    length = len(expression)

    while i < length:
        ch = expression[i]

        # 跳过空白
        if ch in (' ', '\t', '\n', '\r'):
            i += 1
            continue

        # 字段引用 {表名.字段名}
        if ch == '{':
            end = expression.find('}', i)
            if end == -1:
                raise FormulaSyntaxError("未闭合的字段引用 '{'", i)
            ref_content = expression[i + 1:end]
            if '.' not in ref_content:
                raise FormulaSyntaxError(f"字段引用格式错误，应为 {{表名.字段名}}: {{{ref_content}}}", i)
            tokens.append(Token(TokenType.REF, ref_content, i))
            i = end + 1
            continue

        # 字符串字面量（双引号或单引号）
        if ch == '"' or ch == "'":
            quote_char = ch
            end = i + 1
            while end < length and expression[end] != quote_char:
                if expression[end] == '\\':
                    end += 1  # 跳过转义字符
                end += 1
            if end >= length:
                raise FormulaSyntaxError(f"未闭合的字符串（缺少匹配的 {quote_char}）", i)
            str_val = expression[i + 1:end].replace(f'\\{quote_char}', quote_char)
            tokens.append(Token(TokenType.STRING, str_val, i))
            i = end + 1
            continue

        # 数字
        if ch.isdigit() or (ch == '.' and i + 1 < length and expression[i + 1].isdigit()):
            j = i
            has_dot = False
            while j < length and (expression[j].isdigit() or (expression[j] == '.' and not has_dot)):
                if expression[j] == '.':
                    has_dot = True
                j += 1
            num_str = expression[i:j]
            tokens.append(Token(TokenType.NUMBER, float(num_str) if has_dot else int(num_str), i))
            i = j
            continue

        # 括号和逗号
        if ch == '(':
            tokens.append(Token(TokenType.LPAREN, '(', i))
            i += 1
            continue
        if ch == ')':
            tokens.append(Token(TokenType.RPAREN, ')', i))
            i += 1
            continue
        if ch == ',':
            tokens.append(Token(TokenType.COMMA, ',', i))
            i += 1
            continue

        # 运算符
        matched_op = None
        for op in OPERATORS:
            if expression[i:i + len(op)] == op:
                matched_op = op
                break
        if matched_op:
            tokens.append(Token(TokenType.OPERATOR, matched_op, i))
            i += len(matched_op)
            continue

        # 标识符（函数名 或 布尔字面量）
        if ch.isalpha() or ch == '_':
            j = i
            while j < length and (expression[j].isalnum() or expression[j] == '_'):
                j += 1
            word = expression[i:j]
            upper_word = word.upper()
            if upper_word == 'TRUE':
                tokens.append(Token(TokenType.BOOL, True, i))
            elif upper_word == 'FALSE':
                tokens.append(Token(TokenType.BOOL, False, i))
            else:
                tokens.append(Token(TokenType.FUNC, upper_word, i))
            i = j
            continue

        raise FormulaSyntaxError(f"无法识别的字符: '{ch}'", i)

    tokens.append(Token(TokenType.EOF, None, i))
    return tokens


# ============================================================
# AST 节点定义
# ============================================================


@dataclass
class ASTNode:
    pass


@dataclass
class NumberNode(ASTNode):
    value: float | int


@dataclass
class StringNode(ASTNode):
    value: str


@dataclass
class BoolNode(ASTNode):
    value: bool


@dataclass
class RefNode(ASTNode):
    ref: str  # "表名.字段名"


@dataclass
class FuncCallNode(ASTNode):
    name: str
    args: list[ASTNode] = field(default_factory=list)


@dataclass
class BinaryOpNode(ASTNode):
    op: str
    left: ASTNode = None
    right: ASTNode = None


@dataclass
class UnaryMinusNode(ASTNode):
    operand: ASTNode = None


# ============================================================
# 语法分析器 (Parser) — 递归下降
# ============================================================


class Parser:
    """递归下降解析器，产出 AST。

    优先级（从低到高）：
    1. 比较运算: >, <, >=, <=, =, <>
    2. 加法/拼接: +, -, &
    3. 乘法: *, /
    4. 一元: -
    5. 原子: 数字, 字符串, 布尔, 引用, 函数调用, 括号表达式
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, ttype: TokenType) -> Token:
        tok = self.current()
        if tok.type != ttype:
            raise FormulaSyntaxError(
                f"期望 {ttype.value}，实际为 {tok.type.value}('{tok.value}')", tok.position)
        return self.advance()

    def parse(self) -> ASTNode:
        node = self.parse_comparison()
        if self.current().type != TokenType.EOF:
            raise FormulaSyntaxError(
                f"表达式结束后有多余内容: '{self.current().value}'", self.current().position)
        return node

    def parse_comparison(self) -> ASTNode:
        left = self.parse_addition()
        while (self.current().type == TokenType.OPERATOR and
               self.current().value in ('>', '<', '>=', '<=', '=', '<>')):
            op = self.advance().value
            right = self.parse_addition()
            left = BinaryOpNode(op=op, left=left, right=right)
        return left

    def parse_addition(self) -> ASTNode:
        left = self.parse_multiplication()
        while (self.current().type == TokenType.OPERATOR and
               self.current().value in ('+', '-', '&')):
            op = self.advance().value
            right = self.parse_multiplication()
            left = BinaryOpNode(op=op, left=left, right=right)
        return left

    def parse_multiplication(self) -> ASTNode:
        left = self.parse_unary()
        while (self.current().type == TokenType.OPERATOR and
               self.current().value in ('*', '/')):
            op = self.advance().value
            right = self.parse_unary()
            left = BinaryOpNode(op=op, left=left, right=right)
        return left

    def parse_unary(self) -> ASTNode:
        if (self.current().type == TokenType.OPERATOR and self.current().value == '-'):
            self.advance()
            operand = self.parse_unary()
            return UnaryMinusNode(operand=operand)
        return self.parse_atom()

    def parse_atom(self) -> ASTNode:
        tok = self.current()

        if tok.type == TokenType.NUMBER:
            self.advance()
            return NumberNode(value=tok.value)

        if tok.type == TokenType.STRING:
            self.advance()
            return StringNode(value=tok.value)

        if tok.type == TokenType.BOOL:
            self.advance()
            return BoolNode(value=tok.value)

        if tok.type == TokenType.REF:
            self.advance()
            return RefNode(ref=tok.value)

        if tok.type == TokenType.FUNC:
            return self.parse_func_call()

        if tok.type == TokenType.LPAREN:
            self.advance()
            node = self.parse_comparison()
            self.expect(TokenType.RPAREN)
            return node

        raise FormulaSyntaxError(
            f"意外的 Token: {tok.type.value}('{tok.value}')", tok.position)

    def parse_func_call(self) -> ASTNode:
        name_tok = self.advance()  # FUNC token
        self.expect(TokenType.LPAREN)
        args = []
        if self.current().type != TokenType.RPAREN:
            args.append(self.parse_comparison())
            while self.current().type == TokenType.COMMA:
                self.advance()
                args.append(self.parse_comparison())
        self.expect(TokenType.RPAREN)
        return FuncCallNode(name=name_tok.value, args=args)


# ============================================================
# 函数注册表
# ============================================================

FUNCTION_REGISTRY: dict[str, dict] = {}


def register_function(name: str, min_args: int = 0, max_args: int = 999, description: str = '', category: str = '其他'):
    """装饰器：注册公式函数。"""
    def decorator(func):
        FUNCTION_REGISTRY[name.upper()] = {
            'func': func,
            'min_args': min_args,
            'max_args': max_args,
            'description': description,
            'name': name.upper(),
            'category': category,
        }
        return func
    return decorator


# ---------- 逻辑函数 ----------

@register_function('IF', 2, 3, 'IF(条件, 真值, [假值]) — 条件判断', category='逻辑函数')
def func_if(args, ctx):
    cond = args[0]
    if cond:
        return args[1]
    return args[2] if len(args) > 2 else ''


@register_function('AND', 1, 999, 'AND(条件1, 条件2, ...) — 全部为真返回TRUE', category='逻辑函数')
def func_and(args, ctx):
    return all(bool(a) for a in args)


@register_function('OR', 1, 999, 'OR(条件1, 条件2, ...) — 任一为真返回TRUE', category='逻辑函数')
def func_or(args, ctx):
    return any(bool(a) for a in args)


@register_function('NOT', 1, 1, 'NOT(条件) — 取反', category='逻辑函数')
def func_not(args, ctx):
    return not bool(args[0])


@register_function('IFS', 2, 999, 'IFS(条件1, 值1, 条件2, 值2, ...) — 多条件判断', category='逻辑函数')
def func_ifs(args, ctx):
    if len(args) % 2 != 0:
        raise FormulaRuntimeError("IFS函数参数必须成对（条件, 值）")
    for i in range(0, len(args), 2):
        if args[i]:
            return args[i + 1]
    return ''


@register_function('SWITCH', 3, 999, 'SWITCH(表达式, 值1, 结果1, [值2, 结果2, ...], [默认值])', category='逻辑函数')
def func_switch(args, ctx):
    expr_val = args[0]
    i = 1
    while i < len(args) - 1:
        if args[i] == expr_val:
            return args[i + 1]
        i += 2
    # 奇数个剩余参数 → 最后一个是默认值
    if len(args) % 2 == 0:
        return args[-1]
    return ''


@register_function('IFERROR', 2, 2, 'IFERROR(表达式, 错误时返回值)', category='逻辑函数')
def func_iferror(args, ctx):
    # 注意：IFERROR 需要特殊处理，在 eval_node 中实现惰性求值
    return args[0]


# ---------- 文本函数 ----------

@register_function('CONCAT', 1, 999, 'CONCAT(文本1, 文本2, ...) — 拼接文本', category='字符串函数')
def func_concat(args, ctx):
    return ''.join(str(a) if a is not None else '' for a in args)


@register_function('LEFT', 1, 2, 'LEFT(文本, [长度]) — 取左侧字符', category='字符串函数')
def func_left(args, ctx):
    text = str(args[0]) if args[0] is not None else ''
    n = int(args[1]) if len(args) > 1 else 1
    return text[:n]


@register_function('RIGHT', 1, 2, 'RIGHT(文本, [长度]) — 取右侧字符', category='字符串函数')
def func_right(args, ctx):
    text = str(args[0]) if args[0] is not None else ''
    n = int(args[1]) if len(args) > 1 else 1
    return text[-n:] if n > 0 else ''


@register_function('MID', 3, 3, 'MID(文本, 起始位置, 长度) — 取中间字符', category='字符串函数')
def func_mid(args, ctx):
    text = str(args[0]) if args[0] is not None else ''
    start = int(args[1]) - 1  # Excel 从 1 开始
    length = int(args[2])
    return text[start:start + length]


@register_function('LEN', 1, 1, 'LEN(文本) — 文本长度', category='字符串函数')
def func_len(args, ctx):
    return len(str(args[0]) if args[0] is not None else '')


@register_function('TRIM', 1, 1, 'TRIM(文本) — 去除首尾空格', category='字符串函数')
def func_trim(args, ctx):
    return str(args[0]).strip() if args[0] is not None else ''


@register_function('UPPER', 1, 1, 'UPPER(文本) — 转大写', category='字符串函数')
def func_upper(args, ctx):
    return str(args[0]).upper() if args[0] is not None else ''


@register_function('LOWER', 1, 1, 'LOWER(文本) — 转小写', category='字符串函数')
def func_lower(args, ctx):
    return str(args[0]).lower() if args[0] is not None else ''


@register_function('SUBSTITUTE', 3, 4, 'SUBSTITUTE(文本, 旧文本, 新文本, [第N次]) — 替换', category='字符串函数')
def func_substitute(args, ctx):
    text = str(args[0]) if args[0] is not None else ''
    old_text = str(args[1]) if args[1] is not None else ''
    new_text = str(args[2]) if args[2] is not None else ''
    if len(args) > 3:
        # 替换第N次出现
        n = int(args[3])
        count = 0
        result = text
        start = 0
        while True:
            idx = result.find(old_text, start)
            if idx == -1:
                break
            count += 1
            if count == n:
                result = result[:idx] + new_text + result[idx + len(old_text):]
                break
            start = idx + len(old_text)
        return result
    return text.replace(old_text, new_text)


# ---------- 数学函数 ----------

@register_function('ABS', 1, 1, 'ABS(数字) — 绝对值', category='数字函数')
def func_abs(args, ctx):
    return abs(_to_number(args[0]))


@register_function('ROUND', 1, 2, 'ROUND(数字, [小数位]) — 四舍五入', category='数字函数')
def func_round(args, ctx):
    num = _to_number(args[0])
    digits = int(args[1]) if len(args) > 1 else 0
    return round(num, digits)


@register_function('CEILING', 1, 2, 'CEILING(数字, [基数]) — 向上取整', category='数字函数')
def func_ceiling(args, ctx):
    import math
    num = _to_number(args[0])
    significance = _to_number(args[1]) if len(args) > 1 else 1
    if significance == 0:
        return 0
    return math.ceil(num / significance) * significance


@register_function('FLOOR', 1, 2, 'FLOOR(数字, [基数]) — 向下取整', category='数字函数')
def func_floor(args, ctx):
    import math
    num = _to_number(args[0])
    significance = _to_number(args[1]) if len(args) > 1 else 1
    if significance == 0:
        return 0
    return math.floor(num / significance) * significance


@register_function('MOD', 2, 2, 'MOD(被除数, 除数) — 取余', category='数字函数')
def func_mod(args, ctx):
    divisor = _to_number(args[1])
    if divisor == 0:
        raise FormulaRuntimeError("MOD函数除数不能为0")
    return _to_number(args[0]) % divisor


@register_function('MAX', 1, 999, 'MAX(数字1, 数字2, ...) — 最大值', category='数字函数')
def func_max(args, ctx):
    nums = [_to_number(a) for a in args if a is not None and a != '']
    return max(nums) if nums else 0


@register_function('MIN', 1, 999, 'MIN(数字1, 数字2, ...) — 最小值', category='数字函数')
def func_min(args, ctx):
    nums = [_to_number(a) for a in args if a is not None and a != '']
    return min(nums) if nums else 0


# ---------- 判空函数 ----------

@register_function('ISBLANK', 1, 1, 'ISBLANK(值) — 是否为空', category='判空函数')
def func_isblank(args, ctx):
    val = args[0]
    return val is None or val == '' or val == []


@register_function('ISNA', 1, 1, 'ISNA(值) — 是否为NA/None', category='判空函数')
def func_isna(args, ctx):
    return args[0] is None


@register_function('ISNUMBER', 1, 1, 'ISNUMBER(值) — 是否为数字', category='判空函数')
def func_isnumber(args, ctx):
    val = args[0]
    return isinstance(val, (int, float))


@register_function('ISTEXT', 1, 1, 'ISTEXT(值) — 是否为文本', category='判空函数')
def func_istext(args, ctx):
    return isinstance(args[0], str)


# ---------- 日期函数 ----------

@register_function('TODAY', 0, 0, 'TODAY() — 今天日期', category='日期函数')
def func_today(args, ctx):
    return date.today().isoformat()


@register_function('YEAR', 1, 1, 'YEAR(日期) — 取年份', category='日期函数')
def func_year(args, ctx):
    return _parse_date(args[0]).year


@register_function('MONTH', 1, 1, 'MONTH(日期) — 取月份', category='日期函数')
def func_month(args, ctx):
    return _parse_date(args[0]).month


@register_function('DAY', 1, 1, 'DAY(日期) — 取日', category='日期函数')
def func_day(args, ctx):
    return _parse_date(args[0]).day


@register_function('DATEDIF', 3, 3, 'DATEDIF(开始日期, 结束日期, 单位) — 日期差', category='日期函数')
def func_datedif(args, ctx):
    start = _parse_date(args[0])
    end = _parse_date(args[1])
    unit = str(args[2]).upper()
    delta = end - start
    if unit == 'D':
        return delta.days
    elif unit == 'M':
        return (end.year - start.year) * 12 + (end.month - start.month)
    elif unit == 'Y':
        return end.year - start.year
    raise FormulaRuntimeError(f"DATEDIF单位不支持: {unit}，可选 D/M/Y")


# ============================================================
# 辅助函数
# ============================================================

def _to_number(val) -> float:
    """将值转为数字。"""
    if val is None or val == '':
        return 0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val))
    except (ValueError, TypeError):
        raise FormulaRuntimeError(f"无法将 '{val}' 转换为数字")


def _parse_date(val) -> date:
    """将值解析为日期。"""
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y%m%d', '%Y-%m-%d %H:%M:%S'):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    raise FormulaRuntimeError(f"无法将 '{val}' 解析为日期")


# ============================================================
# 求值器
# ============================================================


def eval_node(node: ASTNode, context: dict) -> Any:
    """递归求值 AST 节点。context = {"表名.字段名": 值}"""
    if isinstance(node, NumberNode):
        return node.value

    if isinstance(node, StringNode):
        return node.value

    if isinstance(node, BoolNode):
        return node.value

    if isinstance(node, RefNode):
        ref_key = node.ref
        if ref_key not in context:
            raise FormulaReferenceError(ref_key)
        return context[ref_key]

    if isinstance(node, UnaryMinusNode):
        val = eval_node(node.operand, context)
        return -_to_number(val)

    if isinstance(node, BinaryOpNode):
        left_val = eval_node(node.left, context)
        right_val = eval_node(node.right, context)
        return _eval_binary_op(node.op, left_val, right_val)

    if isinstance(node, FuncCallNode):
        return _eval_func(node, context)

    raise FormulaRuntimeError(f"未知的AST节点类型: {type(node).__name__}")


def _eval_binary_op(op: str, left: Any, right: Any) -> Any:
    """执行二元运算。"""
    if op == '&':
        return str(left if left is not None else '') + str(right if right is not None else '')

    if op in ('=', '<>'):
        eq = (str(left) if left is not None else '') == (str(right) if right is not None else '')
        return eq if op == '=' else not eq

    if op in ('>', '<', '>=', '<='):
        l_num = _to_number(left)
        r_num = _to_number(right)
        if op == '>':
            return l_num > r_num
        elif op == '<':
            return l_num < r_num
        elif op == '>=':
            return l_num >= r_num
        else:
            return l_num <= r_num

    # 算术运算
    l_num = _to_number(left)
    r_num = _to_number(right)
    if op == '+':
        return l_num + r_num
    elif op == '-':
        return l_num - r_num
    elif op == '*':
        return l_num * r_num
    elif op == '/':
        if r_num == 0:
            raise FormulaRuntimeError("除数不能为0")
        return l_num / r_num

    raise FormulaRuntimeError(f"未知运算符: {op}")


def _eval_func(node: FuncCallNode, context: dict) -> Any:
    """执行函数调用。"""
    name = node.name
    if name not in FUNCTION_REGISTRY:
        raise FormulaSyntaxError(f"未知函数: {name}")

    func_info = FUNCTION_REGISTRY[name]
    func = func_info['func']
    min_args = func_info['min_args']
    max_args = func_info['max_args']

    # IFERROR 特殊处理：惰性求值第一个参数
    if name == 'IFERROR':
        if len(node.args) != 2:
            raise FormulaRuntimeError("IFERROR需要2个参数")
        try:
            return eval_node(node.args[0], context)
        except FormulaError:
            return eval_node(node.args[1], context)

    # 正常求值所有参数
    evaluated_args = [eval_node(arg, context) for arg in node.args]

    if len(evaluated_args) < min_args:
        raise FormulaRuntimeError(f"{name}函数至少需要{min_args}个参数，实际{len(evaluated_args)}个")
    if len(evaluated_args) > max_args:
        raise FormulaRuntimeError(f"{name}函数最多接受{max_args}个参数，实际{len(evaluated_args)}个")

    return func(evaluated_args, context)


# ============================================================
# 公开 API
# ============================================================


def evaluate(expression: str, context: dict) -> Any:
    """执行公式表达式。

    Args:
        expression: Excel风格公式字符串
        context: 字段值上下文 {"表名.字段名": 值, ...}

    Returns:
        计算结果

    Raises:
        FormulaSyntaxError: 语法错误
        FormulaReferenceError: 字段引用未找到
        FormulaRuntimeError: 运行时错误
    """
    if not expression or not expression.strip():
        return None
    tokens = tokenize(expression)
    parser = Parser(tokens)
    ast = parser.parse()
    return eval_node(ast, context)


def validate_expression(expression: str) -> dict:
    """验证公式语法，不执行。含函数参数数量校验。

    Returns:
        {"valid": True/False, "error": None/str, "references": [...]}
    """
    if not expression or not expression.strip():
        return {"valid": True, "error": None, "references": []}
    try:
        tokens = tokenize(expression)
        parser = Parser(tokens)
        ast = parser.parse()
        # 验证函数参数数量
        errors = _validate_func_args(ast)
        if errors:
            return {"valid": False, "error": '; '.join(errors), "references": extract_references(expression)}
        refs = extract_references(expression)
        return {"valid": True, "error": None, "references": refs}
    except FormulaError as e:
        return {"valid": False, "error": str(e), "references": extract_references(expression)}


def _validate_func_args(node: ASTNode) -> list[str]:
    """遍历 AST 校验所有函数调用的参数数量。"""
    errors = []
    if isinstance(node, FuncCallNode):
        name = node.name
        n_args = len(node.args)
        if name in FUNCTION_REGISTRY:
            info = FUNCTION_REGISTRY[name]
            if n_args < info['min_args']:
                errors.append(f"{name}函数至少需要{info['min_args']}个参数，实际{n_args}个")
            elif n_args > info['max_args']:
                errors.append(f"{name}函数最多接受{info['max_args']}个参数，实际{n_args}个")
            # IFS 特殊校验：参数必须成对
            if name == 'IFS' and n_args % 2 != 0:
                errors.append(f"IFS函数参数必须成对（条件, 值），当前{n_args}个参数为奇数")
        # 递归检查子参数
        for arg in node.args:
            errors.extend(_validate_func_args(arg))
    elif isinstance(node, BinaryOpNode):
        if node.left:
            errors.extend(_validate_func_args(node.left))
        if node.right:
            errors.extend(_validate_func_args(node.right))
    elif isinstance(node, UnaryMinusNode):
        if node.operand:
            errors.extend(_validate_func_args(node.operand))
    return errors


def get_available_functions() -> list[dict]:
    """返回所有已注册函数的描述列表。"""
    result = []
    for name, info in sorted(FUNCTION_REGISTRY.items()):
        result.append({
            "name": info['name'],
            "min_args": info['min_args'],
            "max_args": info['max_args'],
            "description": info['description'],
            "category": info.get('category', '其他'),
        })
    return result


# ============================================================
# 技术函数插件接入（末尾导入，确保注册表完整）
# ============================================================
from . import custom_functions  # noqa: E402,F401
