"""开放网关鉴权/限流/日志单点（v19，REQ-005 方向承载点）。

拦截链：401（无/无效/吊销/过期密钥）→ 403（API停用/无授权/操作越权）→ 429（限流）。
auth 模块启动后仅替换本文件，网关读写逻辑不受影响。

限流为进程内滑动窗口（重启清零）；多实例部署需换 Redis（技术债，已登记）。
"""
import hashlib
import hmac
import secrets
import threading
import time
from datetime import timedelta

from django.utils import timezone

OPERATIONS = ('read', 'create', 'update', 'delete')

# 进程内限流窗口：{(api_key_id, api_id): [时间戳...]}
_rate_windows = {}
_rate_lock = threading.Lock()


def generate_api_key():
    """生成明文密钥：mdm_+32位随机 hex（明文不落库，仅创建/轮换时返回一次）"""
    return 'mdm_' + secrets.token_hex(16)


def hash_api_key(plain):
    """密钥哈希（SHA-256）"""
    return hashlib.sha256(plain.encode('utf-8')).hexdigest()


def key_prefix(plain):
    """展示用前缀：mdm_xxxx****"""
    return plain[:8] + '****'


def authenticate(request):
    """鉴权第一步：校验 X-API-Key 头。

    返回 (api_key, error)：error 为 None 表示通过；否则为 (status_code, message)。
    通过后顺带更新最近调用时间与累计调用数。
    """
    from .models import ApiKey

    plain = (request.headers.get('X-API-Key') or '').strip()
    if not plain:
        return None, (401, '缺少认证头 X-API-Key')
    try:
        api_key = ApiKey.objects.get(key_hash=hash_api_key(plain))
    except ApiKey.DoesNotExist:
        return None, (401, '无效的 API 密钥')
    # 恒定时间比对防时序侧信道（哈希命中后再校验一次明文派生值）
    if not hmac.compare_digest(api_key.key_hash, hash_api_key(plain)):
        return None, (401, '无效的 API 密钥')
    if api_key.status != ApiKey.Status.ACTIVE:
        return None, (401, 'API 密钥已吊销')
    if api_key.expires_at and api_key.expires_at <= timezone.now():
        return None, (401, 'API 密钥已过期')
    # 使用统计（每次调用更新）
    ApiKey.objects.filter(id=api_key.id).update(
        last_used_at=timezone.now(), total_calls=api_key.total_calls + 1)
    api_key.last_used_at = timezone.now()
    api_key.total_calls += 1
    return api_key, None


def check_grant(api_key, api_obj, operation):
    """鉴权第二步：API 状态 + 授权关系 + 操作范围。

    返回 (grant, error)：error 为 None 表示通过；否则为 (status_code, message)。
    """
    from .models import ApiKeyGrant, ArchiveApi

    if api_obj.status != ArchiveApi.Status.ENABLED:
        return None, (403, '该接口已停用')
    grant = ApiKeyGrant.objects.filter(api_key=api_key, api=api_obj).first()
    if grant is None:
        return None, (403, '该密钥未获得此接口的授权')
    api_ops = api_obj.allowed_operations or ['read']
    grant_ops = grant.allowed_operations or ['read']
    if operation not in api_ops:
        return None, (403, f'该接口未开放 {operation} 操作')
    if operation not in grant_ops:
        return None, (403, f'该密钥未被授予 {operation} 操作')
    return grant, None


def check_rate_limit(api_key, api_obj):
    """鉴权第三步：按密钥维度滑动窗口限流（0=不限）。

    返回 error：None 表示通过；否则为 (status_code, message)。
    """
    limit = api_obj.rate_limit_per_min or 0
    if limit <= 0:
        return None
    now = time.monotonic()
    window_key = (api_key.id, api_obj.id)
    with _rate_lock:
        timestamps = _rate_windows.setdefault(window_key, [])
        cutoff = now - 60
        while timestamps and timestamps[0] <= cutoff:
            timestamps.pop(0)
        if len(timestamps) >= limit:
            return (429, f'请求过于频繁，限流 {limit} 次/分钟，请稍后重试')
        timestamps.append(now)
    return None


def log_call(api_obj, api_key, method, path, status_code, duration_ms, client_ip, error_summary=''):
    """调用日志落库（保留 90 天，由 apps.py daemon 清理）。写入失败不影响主流程。"""
    import logging
    try:
        from .models import ApiCallLog
        ApiCallLog.objects.create(
            api=api_obj,
            api_key=api_key,
            key_name=api_key.name if api_key else '',
            method=method,
            path=str(path)[:300],
            status_code=status_code,
            duration_ms=int(duration_ms),
            client_ip=str(client_ip or '')[:64],
            error_summary=str(error_summary or '')[:200],
        )
    except Exception as e:
        logging.getLogger(__name__).error(f'API 调用日志写入失败: {e}')


def cleanup_old_logs(retention_days=90):
    """清理超过保留期的调用日志（daemon 定期调用），返回删除条数"""
    from .models import ApiCallLog
    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted, _ = ApiCallLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
