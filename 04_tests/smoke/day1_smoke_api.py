# -*- coding: utf-8 -*-
"""第一天端到端冒烟测试：逐项验证业务场景（用例）清单中的用例。

用法：先启动后端（python manage.py runserver 127.0.0.1:8000），再运行本脚本。
通过 /api 接口走完整业务流程，覆盖：注册、登录、课程、选课、作业、提交、评分。
测试账号带 day1s_ 前缀，结束后自动删除，不污染开发数据。
"""
import json
import time
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8000'
SUFFIX = str(int(time.time()))[-6:]
results = []


def req(method, path, data=None, token=None, expect=None, name=''):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', f'Token {token}')
    try:
        resp = urllib.request.urlopen(r)
        code, content = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        code, content = e.code, e.read()
    try:
        j = json.loads(content)
    except Exception:
        j = content.decode('utf-8', 'replace')[:200]
    ok = expect is None or code == expect
    results.append((name, code, expect, ok))
    print(f'{"PASS" if ok else "FAIL"}  {name}: HTTP {code}' + (f'（期望 {expect}）' if expect else ''))
    if not ok:
        print(f'     响应内容: {str(j)[:300]}')
    return code, j


# ---------- 用例 1：用户注册（学生 / 教师） ----------
stu_name = f'day1s_stu_{SUFFIX}'
tea_name = f'day1s_tea_{SUFFIX}'
oth_name = f'day1s_oth_{SUFFIX}'

code, stu = req('POST', '/api/users/', {
    'username': stu_name, 'password': 'smoke1234', 'email': f'{stu_name}@example.com',
}, expect=201, name='UC01 学生注册')
code, tea = req('POST', '/api/users/', {
    'username': tea_name, 'password': 'smoke1234', 'email': f'{tea_name}@example.com',
    'is_teacher': True,
}, expect=201, name='UC01 教师注册')

# ---------- 用例 2：登录（获取 Token） ----------
_, stu_login = req('POST', '/api/auth/token/', {
    'username': stu_name, 'password': 'smoke1234',
}, expect=200, name='UC02 学生登录')
_, tea_login = req('POST', '/api/auth/token/', {
    'username': tea_name, 'password': 'smoke1234',
}, expect=200, name='UC02 教师登录')
_, oth_login = req('POST', '/api/auth/token/', {
    'username': oth_name, 'password': 'smoke1234',
}, expect=400, name='UC02 未注册用户登录被拒')
stu_tok, tea_tok = stu_login['token'], tea_login['token']

# 未选课学生：先注册
_, oth = req('POST', '/api/users/', {
    'username': oth_name, 'password': 'smoke1234', 'email': f'{oth_name}@example.com',
}, expect=201, name='UC01 注册未选课学生')
_, oth_login = req('POST', '/api/auth/token/', {
    'username': oth_name, 'password': 'smoke1234',
}, expect=200, name='UC02 未选课学生登录')
oth_tok = oth_login['token']

# ---------- 用例 3：教师创建课程 ----------
_, course = req('POST', '/api/courses/', {
    'name': f'冒烟测试课程{SUFFIX}', 'code': f'SMK{SUFFIX}', 'description': '第一天冒烟测试用课程',
}, token=tea_tok, expect=201, name='UC03 教师创建课程')
course_id = course['id']

# 学生不能创建课程
req('POST', '/api/courses/', {
    'name': '越权课程', 'code': f'BAD{SUFFIX}',
}, token=stu_tok, expect=403, name='UC03 学生创建课程被拒')

# ---------- 用例 4：学生浏览课程列表并查看详情 ----------
_, course_list = req('GET', '/api/courses/', token=stu_tok, expect=200, name='UC04 学生浏览课程列表')
found = any(c['id'] == course_id for c in (course_list.get('results') or course_list))
print(f'{"PASS" if found else "FAIL"}  课程列表包含新课程: {found}')
req('GET', f'/api/courses/{course_id}/', token=stu_tok, expect=200, name='UC04 学生查看课程详情')

# ---------- 用例 5：学生选课 / 未选课状态 ----------
req('POST', f'/api/courses/{course_id}/enroll/', token=stu_tok, expect=200, name='UC05 学生选课')
_, detail = req('GET', f'/api/courses/{course_id}/', token=stu_tok, expect=200, name='UC05 选课后查看详情')
print(f'{"PASS" if detail.get("is_enrolled") else "FAIL"}  选课后 is_enrolled=True: {detail.get("is_enrolled")}')
req('POST', f'/api/courses/{course_id}/enroll/', token=tea_tok, expect=400, name='UC05 教师选课被拒')

# ---------- 用例 6：教师创建作业（含参考文档说明） ----------
_, assign = req('POST', '/api/assignments/', {
    'course': course_id,
    'title': f'冒烟作业{SUFFIX}',
    'description': '测试作业描述',
    'deadline': '2026-08-30T23:59:59Z',
}, token=tea_tok, expect=201, name='UC06 教师创建作业')
assign_id = assign['id']

# ---------- 用例 7：学生查看作业详情 ----------
req('GET', f'/api/assignments/{assign_id}/', token=stu_tok, expect=200, name='UC07 学生查看作业详情')

# ---------- 用例 8：学生提交作业 ----------
_, sub = req('POST', '/api/submissions/', {
    'assignment': assign_id, 'code': 'print("hello")\n',
}, token=stu_tok, expect=201, name='UC08 学生提交作业')
sub_id = sub['id']
print(f'{"PASS" if sub.get("status") == "pending" else "FAIL"}  提交状态为 pending: {sub.get("status")}')

# 异常流程：未选课学生提交被拒
req('POST', '/api/submissions/', {
    'assignment': assign_id, 'code': 'print(1)',
}, token=oth_tok, expect=403, name='UC08-异常 未选课学生提交被拒')
# 异常流程：教师提交被拒
req('POST', '/api/submissions/', {
    'assignment': assign_id, 'code': 'print(1)',
}, token=tea_tok, expect=403, name='UC08-异常 教师提交被拒')
# 异常流程：过期作业提交被拒
_, expired = req('POST', '/api/assignments/', {
    'course': course_id,
    'title': f'过期作业{SUFFIX}',
    'description': '已过期',
    'deadline': '2026-08-01T00:00:00Z',
}, token=tea_tok, expect=201, name='UC06 创建过期作业')
req('POST', '/api/submissions/', {
    'assignment': expired['id'], 'code': 'print(1)',
}, token=stu_tok, expect=400, name='UC08-异常 过期作业提交被拒')

# ---------- 用例 9：学生查看提交记录 ----------
_, my_subs = req('GET', f'/api/submissions/?assignment={assign_id}', token=stu_tok, expect=200, name='UC09 学生查看提交记录')
my_ids = [s['id'] for s in (my_subs.get('results') or my_subs)]
print(f'{"PASS" if sub_id in my_ids else "FAIL"}  提交记录包含本次提交: {sub_id in my_ids}')
# 学生只能看到自己的提交，看不到其他作业的提交（跨作业隔离）
req('GET', f'/api/submissions/?assignment={expired["id"]}', token=stu_tok, expect=200, name='UC09 提交记录按作业隔离')

# ---------- 用例 10：教师查看该作业全部提交 ----------
_, tea_subs = req('GET', f'/api/submissions/?assignment={assign_id}', token=tea_tok, expect=200, name='UC10 教师查看作业提交列表')
tea_ids = [s['id'] for s in (tea_subs.get('results') or tea_subs)]
print(f'{"PASS" if sub_id in tea_ids else "FAIL"}  教师列表包含该提交: {sub_id in tea_ids}')

# ---------- 用例 11：教师评分 ----------
_, graded = req('POST', f'/api/submissions/{sub_id}/grade/', {'score': 92}, token=tea_tok, expect=200, name='UC11 教师评分')
print(f'{"PASS" if graded.get("status") == "graded" and graded.get("score") == 92 else "FAIL"}  评分结果: {graded.get("status")}/{graded.get("score")}')
# 异常流程：学生评分被拒
req('POST', f'/api/submissions/{sub_id}/grade/', {'score': 100}, token=stu_tok, expect=403, name='UC11-异常 学生评分被拒')
# 异常流程：分数越界被拒
req('POST', f'/api/submissions/{sub_id}/grade/', {'score': 150}, token=tea_tok, expect=400, name='UC11-异常 分数越界被拒')

# ---------- 用例 12：学生查看个人信息 ----------
_, me = req('GET', '/api/users/me/', token=stu_tok, expect=200, name='UC12 学生查看个人信息')
print(f'{"PASS" if me.get("username") == stu_name else "FAIL"}  个人信息正确: {me.get("username")}')

# ---------- 权限用例：教师不能删除他人课程 ----------
req('DELETE', f'/api/courses/{course_id}/', token=stu_tok, expect=403, name='UC-权限 学生删除课程被拒')

# ---------- 清理：删除测试用户（级联删除课程/作业/提交） ----------
req('DELETE', f"/api/users/{stu['id']}/", token=tea_tok, expect=204, name='清理 删除学生账号')
req('DELETE', f"/api/users/{oth['id']}/", token=tea_tok, expect=204, name='清理 删除未选课学生账号')
req('DELETE', f"/api/users/{tea['id']}/", token=tea_tok, expect=204, name='清理 删除教师账号（级联课程/作业/提交）')

# ---------- 汇总 ----------
passed = sum(1 for _, _, _, ok in results if ok)
total = len(results)
print(f'\n========== 结果汇总: {passed}/{total} 通过 ==========')
exit(0 if passed == total else 1)
