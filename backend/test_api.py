"""API 全面集成测试"""
import json, urllib.request, sys

BASE = "http://localhost:8000/api"

def api(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data, ensure_ascii=False).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

ok, fail = 0, 0
def check(step, expected_status, actual):
    global ok, fail
    status, data = actual
    if status == expected_status:
        ok += 1
        print(f"  [OK] {step} (HTTP {status})")
    else:
        fail += 1
        print(f"  [FAIL] {step} (expected {expected_status}, got {status}): {json.dumps(data, ensure_ascii=False)[:120]}")

print("=" * 60)
print("MODELING API Tests")
print("=" * 60)

# 1. Create Domain
print("\n--- Domain CRUD ---")
r = api("POST", "/domains/", {"name":"供应商","code":"SUPPLIER","description":"供应商主数据"})
check("创建域", 201, r)

r = api("POST", "/domains/", {"name":"客户","code":"CUSTOMER","description":"客户主数据"})
check("创建域2", 201, r)

r = api("GET", "/domains/")
check("域列表", 200, r)
domains = r[1].get("results", [])
print(f"    域数量: {len(domains)}")

# 2. Table
print("\n--- Table CRUD ---")
r = api("POST", "/tables/", {"domain":1,"name":"供应商基本信息","code":"SUPPLIER_BASE","type":"local"})
check("创建本地表", 201, r)

r = api("POST", "/tables/", {"domain":1,"name":"供应商财务信息","code":"SUPPLIER_FIN","type":"source",
        "source_config":{"host":"192.168.1.100","port":"5432","db_name":"erp","table_name":"supplier_fin"}})
check("创建数据源表", 201, r)

r = api("GET", "/tables/?domain=1")
check("表列表", 200, r)
tables = r[1].get("results", [])
print(f"    表数量: {len(tables)}")

# 3. Field
print("\n--- Field CRUD ---")
fields_data = [
    {"name":"公司名称","code":"company_name","sort_order":1},
    {"name":"统一社会信用代码","code":"credit_code","sort_order":2},
    {"name":"法定代表人","code":"legal_person","sort_order":3},
    {"name":"注册资本","code":"registered_capital","sort_order":4},
    {"name":"成立日期","code":"establish_date","sort_order":5},
]
r = api("POST", "/fields/batch/?table=1", {"fields": fields_data})
check("批量保存字段", 201, r)

r = api("GET", "/fields/?table=1")
check("字段列表", 200, r)
fields = r[1].get("results", [])
print(f"    字段数量: {len(fields)}")

if fields:
    field_id = fields[0]["id"]
    r = api("PUT", f"/fields/{field_id}/deprecate/")
    check("作废字段", 200, r)

# 4. Field Group
print("\n--- Field Group ---")
r = api("POST", "/field-groups/", {"domain":1,"name":"基础信息","sort_order":1})
check("创建分组", 201, r)

r = api("POST", "/field-groups/", {"domain":1,"name":"财务信息","sort_order":2})
check("创建分组2", 201, r)

r = api("GET", "/field-groups/?domain=1")
check("分组列表", 200, r)

# 5. Field Mapping
print("\n--- Field Mapping ---")
r = api("POST", "/field-mappings/", {"source_table":1,"source_field":1,"target_table":1,"target_field":2})
check("创建字段映射", 201, r)  # Note: might fail due to missing target_field parameter

# Wait, let me look at the field mapping serializer - it has source_field and target_field both required
# Let me check...

print("\n" + "=" * 60)
print("ARCHIVE API Tests")
print("=" * 60)

# 6. Archive Record
print("\n--- Archive Record CRUD ---")
r = api("POST", "/records/", {
    "domain":1, "table":1,
    "data":{"company_name":"测试公司","credit_code":"91110000MA12345678","legal_person":"张三","registered_capital":"1000","establish_date":"2020-01-01"},
    "created_by":"admin"
})
check("创建档案", 201, r)

r = api("GET", "/records/?domain=1")
check("档案列表", 200, r)
records = r[1].get("results", [])
print(f"    档案数量: {len(records)}")

if records:
    rid = records[0]["id"]
    # 更新
    r = api("PUT", f"/records/{rid}/", {
        "data":{"company_name":"测试公司（更名）","credit_code":"91110000MA12345678","legal_person":"张三","registered_capital":"2000","establish_date":"2020-01-01"},
        "updated_by":"admin"
    })
    check("更新档案", 200, r)

    # 版本列表
    r = api("GET", f"/records/{rid}/versions/")
    check("版本列表", 200, r)
    versions = r[1].get("results", [])
    print(f"    版本数量: {len(versions)}")

    # 版本对比
    r = api("GET", f"/records/{rid}/versions/compare/?v1=1&v2=2")
    check("版本对比", 200, r)
    if r[0] == 200:
        print(f"    差异字段数: {len(r[1].get('diff', []))}")

    # 回滚
    r = api("POST", f"/records/{rid}/rollback/", {"target_version":1,"operated_by":"admin"})
    check("回滚到v1", 200, r)

    # 删除（软删除）
    r = api("DELETE", f"/records/{rid}/")
    check("软删除档案", 204, r)

# 7. Operation Log
print("\n--- Operation Log ---")
r = api("GET", "/operation-logs/")
check("日志列表", 200, r)

print("\n" + "=" * 60)
print(f"=== PASS: {ok} | FAIL: {fail} | TOTAL: {ok+fail} ===")
print("=" * 60)
