"""技术函数插件动态加载器。

支持技术人员通过前端上传 .py 脚本，后端 AST 安全校验后动态加载到公式引擎
FUNCTION_REGISTRY，无需重启服务。

核心能力：
- validate_plugin_code: AST 静态扫描（白名单导入 + 禁止危险操作）
- load_plugin: 从 tech_plugins/ 动态加载单个插件
- unload_plugin: 卸载插件（从注册表移除其注册的所有函数）
- reload_plugin: 重载（先卸载旧注册再重新加载）
- list_plugins: 列出所有已加载插件及注册函数
- load_all_plugins: 启动时扫描 tech_plugins/ 加载全部

安全策略：
- 白名单导入：re / hashlib / math / datetime / apps.modeling.formula_engine
- 禁止：os / sys / subprocess / socket / shutil / builtins / __import__ / eval / exec
- 禁止：文件操作(open/io)、网络、进程、反射类(getattr/setattr)
- 禁止：类定义、顶层控制流（if/for/while/try 允许函数体内）
"""
import ast
import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path

from django.conf import settings

from .formula_engine import FUNCTION_REGISTRY, register_function  # noqa: F401

logger = logging.getLogger(__name__)

# 插件目录：backend/tech_plugins/
PLUGINS_DIR = Path(settings.BASE_DIR) / 'tech_plugins'

# 已加载插件状态：{filename: {'functions': ['FUNC1', 'FUNC2'], 'path': Path}}
_loaded_plugins: dict[str, dict] = {}

# 白名单：插件允许导入的模块
ALLOWED_IMPORTS = {
    're', 'hashlib', 'math', 'datetime', 'time',
    'collections', 'itertools', 'functools',
    'apps.modeling.formula_engine',
    'formula_engine',  # 相对导入备选
}

# 黑名单：禁止导入的模块（前缀匹配）
FORBIDDEN_IMPORT_PREFIXES = (
    'os', 'sys', 'subprocess', 'socket', 'shutil', 'builtins',
    'importlib', 'ctypes', 'threading', 'multiprocessing', 'signal',
    'io', 'pathlib', 'tempfile', 'glob', 'pickle', 'shelve',
    'sqlite3', 'dbm', 'http', 'urllib', 'requests', 'ftplib',
    'smtplib', 'xmlrpc', 'asyncio', 'concurrent', 'contextlib',
    'code', 'codeop', 'compile', 'compileall',
)

# 禁止的顶层/内建名称
FORBIDDEN_NAMES = {
    'eval', 'exec', 'compile', '__import__', 'open', 'input',
    'getattr', 'setattr', 'delattr', 'hasattr',
    'globals', 'locals', 'vars', 'dir',
    'breakpoint', 'exit', 'quit', 'help',
}

FORBIDDEN_ATTRS = {'__import__', '__builtins__', '__file__', '__loader__', '__spec__'}


class PluginError(Exception):
    """插件相关异常。"""


def validate_plugin_code(source: str) -> list[str]:
    """AST 静态安全校验。返回错误列表，空列表表示通过。

    校验规则：
    1. 语法正确（ast.parse 通过）
    2. 所有 import 均在白名单内
    3. 无危险内建调用（eval/exec/open/__import__ 等）
    4. 无类定义、无顶层控制流（if/for/while/try 仅允许函数体内）
    5. 无访问 __import__/__builtins__/__file__ 等私有属性
    """
    errors: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"语法错误（行{e.lineno}）：{e.msg}"]

    for node in ast.walk(tree):
        # 顶层控制流
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
            errors.append(f"行{node.lineno}：顶层不允许 {type(node).__name__} 语句（请放入函数体内）")
            continue
        if isinstance(node, ast.ClassDef):
            errors.append(f"行{node.lineno}：不允许定义类")
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _is_import_allowed(alias.name):
                    errors.append(f"行{node.lineno}：禁止导入 '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            if not _is_import_allowed(mod):
                errors.append(f"行{node.lineno}：禁止从 '{mod}' 导入")
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in FORBIDDEN_NAMES:
                errors.append(f"行{node.lineno}：禁止调用 '{fn.id}'")
            elif isinstance(fn, ast.Attribute) and fn.attr in FORBIDDEN_ATTRS:
                errors.append(f"行{node.lineno}：禁止访问 '{fn.attr}'")

    return errors


def _is_import_allowed(module_name: str) -> bool:
    if not module_name:
        return False
    if module_name in ALLOWED_IMPORTS:
        return True
    if any(module_name.startswith(p + '.') or module_name == p for p in FORBIDDEN_IMPORT_PREFIXES):
        return False
    # 相对导入 apps.modeling.formula_engine 的子模块
    if module_name.startswith('apps.modeling.'):
        return True
    return False


def _ensure_plugins_dir() -> Path:
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    return PLUGINS_DIR


def load_plugin(filename: str) -> dict:
    """加载单个插件。filename 必须以 .py 结尾。返回插件信息。

    如果同名插件已加载，先卸载旧的再加载新的（覆盖语义）。
    """
    _ensure_plugins_dir()
    if not filename.endswith('.py'):
        raise PluginError('文件名必须以 .py 结尾')
    path = PLUGINS_DIR / filename
    if not path.exists():
        raise PluginError(f'文件不存在：{filename}')

    # 同名覆盖：先卸载旧版
    if filename in _loaded_plugins:
        _do_unload(filename)

    source = path.read_text(encoding='utf-8')
    errs = validate_plugin_code(source)
    if errs:
        raise PluginError('安全校验失败：' + '；'.join(errs))

    # 动态加载
    module_name = f'tech_plugins_plugin_{filename[:-3]}'
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise PluginError(f'无法加载模块：{filename}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    before = set(FUNCTION_REGISTRY.keys())
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # 回滚：移除刚加载的模块
        sys.modules.pop(module_name, None)
        raise PluginError(f'执行插件失败：{e}') from e
    after = set(FUNCTION_REGISTRY.keys())

    new_fns = sorted(after - before)
    if not new_fns:
        sys.modules.pop(module_name, None)
        raise PluginError('插件未注册任何函数（需使用 @register_function 装饰器）')

    # 标记 source
    for fn in new_fns:
        FUNCTION_REGISTRY[fn]['source'] = filename

    _loaded_plugins[filename] = {
        'functions': new_fns,
        'path': str(path),
        'module_name': module_name,
    }
    logger.info('加载技术函数插件 %s，注册函数：%s', filename, new_fns)
    return {
        'filename': filename,
        'functions': new_fns,
        'source': filename,
    }


def _do_unload(filename: str):
    info = _loaded_plugins.pop(filename, None)
    if not info:
        return
    for fn in info['functions']:
        if fn in FUNCTION_REGISTRY and FUNCTION_REGISTRY[fn].get('source') == filename:
            del FUNCTION_REGISTRY[fn]
    sys.modules.pop(info.get('module_name'), None)
    logger.info('卸载技术函数插件 %s，移除函数：%s', filename, info['functions'])


def unload_plugin(filename: str):
    """卸载插件。"""
    if filename not in _loaded_plugins:
        raise PluginError(f'插件未加载：{filename}')
    _do_unload(filename)


def reload_plugin(filename: str) -> dict:
    """重载插件（重新读取文件并重新注册）。"""
    if filename not in _loaded_plugins:
        raise PluginError(f'插件未加载：{filename}')
    path = PLUGINS_DIR / filename
    if not path.exists():
        raise PluginError(f'文件不存在：{filename}')
    _do_unload(filename)
    return load_plugin(filename)


def list_plugins() -> list[dict]:
    """列出所有已加载插件及其注册的函数。"""
    result = []
    for filename, info in _loaded_plugins.items():
        fns = []
        for fn in info['functions']:
            reg = FUNCTION_REGISTRY.get(fn)
            if reg:
                fns.append({
                    'name': reg['name'],
                    'category': reg.get('category', '其他'),
                    'description': reg.get('description', ''),
                })
        result.append({
            'filename': filename,
            'functions': fns,
            'function_count': len(fns),
        })
    return result


def load_all_plugins():
    """启动时扫描 tech_plugins/ 加载全部 .py 文件。失败记录日志不中断启动。"""
    _ensure_plugins_dir()
    files = sorted(f.name for f in PLUGINS_DIR.iterdir() if f.is_file() and f.suffix == '.py')
    for fn in files:
        try:
            load_plugin(fn)
        except PluginError as e:
            logger.warning('启动加载插件 %s 失败：%s', fn, e)


def get_plugin_template() -> str:
    """返回插件模板代码，供前端下载。"""
    return '''"""技术函数插件示例。

上传本文件到「技术函数管理」页面即可加载。
修改本文件中的函数实现或新增 @register_function 装饰的函数即可扩展公式引擎。
"""
import re
from apps.modeling.formula_engine import FormulaRuntimeError, register_function


@register_function(
    'MY_FUNC', 2, 2,
    'MY_FUNC(文本, 后缀) — 示例函数：拼接后缀',
    category='技术函数',
)
def func_my_func(args, ctx):
    text = '' if args[0] is None else str(args[0])
    suffix = '' if args[1] is None else str(args[1])
    return text + suffix


@register_function(
    'REGEX_MATCH', 2, 2,
    'REGEX_MATCH(文本, 正则) — 是否匹配正则，返回 TRUE/FALSE',
    category='技术函数',
)
def func_regex_match(args, ctx):
    text = '' if args[0] is None else str(args[0])
    try:
        return bool(re.search(str(args[1]), text))
    except re.error as e:
        raise FormulaRuntimeError(f"REGEX_MATCH正则无效: {e}")
'''
