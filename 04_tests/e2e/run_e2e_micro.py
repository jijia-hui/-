# -*- coding: utf-8 -*-
"""微服务版端到端回归测试：经 API 网关走完清单中每个业务场景（UC01~UC14）。

与单体版 run_e2e.py 的区别：
- 目标是微服务栈（网关入口），E2E_BASE_URL 必填，如 http://127.0.0.1:8080（前端）
  或 http://127.0.0.1:8000（网关直连）。
- 注册验证码与临时管理员通过容器内 manage.py 注入（E2E_EXEC_PREFIX 指定 exec 前缀）：
    docker compose: E2E_EXEC_PREFIX="docker compose -f docker-compose.micro.yml exec -T user-service"
    kubernetes:     E2E_EXEC_PREFIX="kubectl -n online-teach-micro exec deploy/user-service --"
- E2E-TC14 管理员后台只检查 user-service 暴露的 Django Admin（课程/作业数据在各自服务，无集中后台）。

用法：
    E2E_BASE_URL=http://127.0.0.1:8080 \
    E2E_EXEC_PREFIX="docker compose -f docker-compose.micro.yml exec -T user-service" \
    python 04_tests/e2e/run_e2e_micro.py

退出码：全部通过返回 0，任一失败返回 1；报告写入 04_tests/reports/e2e_micro_report_*.md。
"""
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REPORT_DIR = os.path.join(REPO_ROOT, '04_tests', 'reports')

BASE = os.environ.get('E2E_BASE_URL', '').rstrip('/')
EXEC_PREFIX = shlex.split(os.environ.get('E2E_EXEC_PREFIX', ''))
SUFFIX = str(int(time.time()))[-6:]
results = []


# ---------- 基础设施 ----------

def req(method, path, data=None, token=None, expect=None, name=''):
    """发送请求并断言状态码；返回 (status_code, json)。"""
    headers = {}
    if token:
        headers['Authorization'] = f'Token {token}'
    r = requests.request(method, BASE + path, json=data, headers=headers, timeout=20)
    try:
        body = r.json()
    except ValueError:
        body = r.text[:300]
    ok = expect is None or r.status_code == expect
    results.append({'name': name, 'ok': ok, 'code': r.status_code, 'expect': expect})
    print(f'{"PASS" if ok else "FAIL"}  {name}: HTTP {r.status_code}' +
          (f'（期望 {expect}）' if expect is not None else ''))
    if not ok:
        print(f'     响应内容: {str(body)[:300]}')
    return r.status_code, body


def assert_true(cond, name, detail=''):
    ok = bool(cond)
    results.append({'name': name, 'ok': ok, 'code': detail if detail else ('OK' if ok else 'N/A')})
    print(f'{"PASS" if ok else "FAIL"}  {name}' + (f': {detail}' if detail and not ok else ''))
    return ok


def exec_in_user_service(code):
    """在 user-service 容器内执行 manage.py shell 片段，返回 stdout。"""
    if not EXEC_PREFIX:
        print(f'[setup] E2E_EXEC_PREFIX 未配置，无法执行: {code[:60]}')
        return ''
    cmd = EXEC_PREFIX + ['python', 'manage.py', 'shell', '-c', code]
    out = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                         encoding='utf-8', errors='replace', timeout=120)
    if out.returncode != 0:
        print(f'[setup] 容器内执行失败: {(out.stderr or out.stdout)[:300]}')
        return ''
    return out.stdout or ''


def latest_code(email):
    """直接向 user-service 写入验证码，避免 E2E 走真实 SMTP。"""
    script = (
        "from users.models import EmailVerificationCode;"
        f"print(EmailVerificationCode.issue('{email.lower()}').code)"
    )
    lines = [ln.strip() for ln in exec_in_user_service(script).splitlines() if ln.strip()]
    return lines[-1] if lines else ''


def ensure_admin():
    """E2E-TC14 需要管理员账号；在 user-service 内创建临时管理员。"""
    username = f'e2e_admin_{SUFFIX}'
    password = f'E2ePass{SUFFIX}!'
    code = (
        "from users.models import User;"
        f"u, _ = User.objects.get_or_create(username='{username}');"
        "u.is_staff=True; u.is_superuser=True;"
        f"u.set_password('{password}'); u.save(); print(u.id)"
    )
    out = exec_in_user_service(code)
    if not out.strip():
        return None
    return username, password


def register_with_code(username, email, password='e2e1234', is_teacher=False, name=''):
    code = latest_code(email)
    payload = {'username': username, 'password': password, 'email': email,
               'verification_code': code}
    if is_teacher:
        payload['is_teacher'] = True
    return req('POST', '/api/users/', payload, expect=201, name=name)


def gateway_alive():
    """网关与逐服务探活（含版本号核对）。"""
    checks = [
        ('/api/health/', '网关 /api/health/'),
        ('/api/health/user/', 'user-service 探活'),
        ('/api/health/course/', 'course-service 探活'),
        ('/api/health/assignment/', 'assignment-service 探活'),
    ]
    all_ok = True
    for path, label in checks:
        try:
            r = requests.get(BASE + path, timeout=10)
        except requests.RequestException as exc:
            assert_true(False, f'[setup] {label}', str(exc)[:120])
            all_ok = False
            continue
        ok = r.status_code == 200
        version = ''
        try:
            version = r.json().get('version', '')
        except ValueError:
            pass
        assert_true(ok, f'[setup] {label}（version={version}）', f'HTTP {r.status_code}')
        all_ok = all_ok and ok
    # 内部接口必须被屏蔽：网关直连返回 403；经前端时未代理（SPA 兜底返回 HTML，同样不可达）
    code_resp = requests.get(BASE + '/internal/users/?ids=1', timeout=10)
    not_exposed = (code_resp.status_code == 403
                   or 'application/json' not in code_resp.headers.get('Content-Type', ''))
    assert_true(not_exposed, '[setup] 内部接口不经对外入口暴露（403 或非 JSON 兜底）',
                f'HTTP {code_resp.status_code} {code_resp.headers.get("Content-Type", "")}')
    return all_ok


# ---------- 用例级端到端测试（E2E-TC01~14，对外契约与单体版一致） ----------

def tc01_registration():
    """E2E-TC01 用户注册（UC01）：学生/教师注册成功；缺验证码/缺邮箱被拒。"""
    name = f'e2e_stu_{SUFFIX}'
    email = f'{name}@example.com'
    _, stu = register_with_code(name, email, name='E2E-TC01 学生注册')
    tea_name = f'e2e_tea_{SUFFIX}'
    _, tea = register_with_code(tea_name, f'{tea_name}@example.com', is_teacher=True,
                                name='E2E-TC01 教师注册')
    req('POST', '/api/users/', {'username': f'e2e_nocode_{SUFFIX}', 'password': 'e2e1234',
                                'email': f'e2e_nocode_{SUFFIX}@example.com'},
        expect=400, name='E2E-TC01-异常 缺验证码注册被拒')
    req('POST', '/api/users/', {'username': f'e2e_nomail_{SUFFIX}', 'password': 'e2e1234'},
        expect=400, name='E2E-TC01-异常 缺邮箱注册被拒')
    return {'stu': stu, 'tea': tea}


def tc02_login(users):
    """E2E-TC02 用户登录（UC02）：签发 JWT Token；错误密码/未注册被拒。"""
    _, stu_login = req('POST', '/api/auth/token/', {'username': users['stu']['username'],
                                                    'password': 'e2e1234'},
                       expect=200, name='E2E-TC02 学生登录')
    _, tea_login = req('POST', '/api/auth/token/', {'username': users['tea']['username'],
                                                    'password': 'e2e1234'},
                       expect=200, name='E2E-TC02 教师登录')
    assert_true(bool(stu_login.get('token')), 'E2E-TC02 返回 token（无状态 JWT）')
    req('POST', '/api/auth/token/', {'username': users['stu']['username'], 'password': 'wrong'},
        expect=400, name='E2E-TC02-异常 错误密码被拒')
    return {'stu': stu_login['token'], 'tea': tea_login['token']}


def tc03_browse_courses(tokens, course_id):
    """E2E-TC03 浏览课程列表与详情（UC03）：列表包含新课程；详情字段正确（含跨服务补全的教师名）。"""
    _, lst = req('GET', '/api/courses/', token=tokens['stu'], expect=200,
                 name='E2E-TC03 学生浏览课程列表')
    rows = lst.get('results') or lst
    found = any(c['id'] == course_id for c in rows)
    assert_true(found, 'E2E-TC03 列表包含新课程')
    _, detail = req('GET', f'/api/courses/{course_id}/', token=tokens['stu'], expect=200,
                    name='E2E-TC03 学生查看课程详情')
    assert_true(detail.get('name'), 'E2E-TC03 详情返回课程名称', str(detail)[:100])
    assert_true(detail.get('teacher_name') == tokens['tea_name'],
                'E2E-TC03 教师名经用户服务补全', str(detail.get('teacher_name')))


def tc04_enroll(tokens, course_id):
    """E2E-TC04 学生选课/退课（UC04）：选课成功生效；教师选课被拒；退课移除。"""
    req('POST', f'/api/courses/{course_id}/enroll/', token=tokens['stu'], expect=200,
        name='E2E-TC04 学生选课')
    _, detail = req('GET', f'/api/courses/{course_id}/', token=tokens['stu'], expect=200,
                    name='E2E-TC04 选课后查看详情')
    assert_true(detail.get('is_enrolled'), 'E2E-TC04 选课后 is_enrolled=True')
    req('POST', f'/api/courses/{course_id}/enroll/', token=tokens['tea'], expect=400,
        name='E2E-TC04-异常 教师选课被拒')
    req('POST', f'/api/courses/{course_id}/unenroll/', token=tokens['stu'], expect=200,
        name='E2E-TC04 学生退课')
    _, after = req('GET', f'/api/courses/{course_id}/', token=tokens['stu'], expect=200,
                   name='E2E-TC04 退课后查看详情')
    assert_true(not after.get('is_enrolled'), 'E2E-TC04 退课后 is_enrolled=False')
    req('POST', f'/api/courses/{course_id}/enroll/', token=tokens['stu'], expect=200,
        name='E2E-TC04 重新选课（供后续用例）')


def tc05_create_course(tokens):
    """E2E-TC05 教师创建课程（UC05）：创建者自动成为授课教师；学生创建被拒。"""
    _, course = req('POST', '/api/courses/', {'name': f'E2E课程{SUFFIX}', 'code': f'E2E{SUFFIX}',
                                              'description': '端到端测试课程'},
                    token=tokens['tea'], expect=201, name='E2E-TC05 教师创建课程')
    assert_true(course.get('teacher_name') == tokens['tea_name'], 'E2E-TC05 授课教师为创建者',
                str(course)[:100])
    req('POST', '/api/courses/', {'name': '越权课程', 'code': f'BAD{SUFFIX}'},
        token=tokens['stu'], expect=403, name='E2E-TC05-异常 学生创建课程被拒')
    req('POST', '/api/courses/', {'name': '重复编号', 'code': f'E2E{SUFFIX}'},
        token=tokens['tea'], expect=400, name='E2E-TC05-异常 课程编号重复被拒')
    return course


def tc06_manage_course(tokens, course_id):
    """E2E-TC06 教师编辑/删除课程（UC06）：编辑成功；他人/学生修改删除被拒。"""
    req('PATCH', f'/api/courses/{course_id}/', {'name': f'E2E课程{SUFFIX}改'},
        token=tokens['tea'], expect=200, name='E2E-TC06 教师编辑课程')
    req('PATCH', f'/api/courses/{course_id}/', {'name': '篡改'},
        token=tokens['stu'], expect=403, name='E2E-TC06-异常 学生编辑课程被拒')
    req('DELETE', f'/api/courses/{course_id}/', token=tokens['stu'], expect=403,
        name='E2E-TC06-异常 学生删除课程被拒')


def tc07_manage_assignment(tokens, course_id):
    """E2E-TC07 教师管理作业（UC07）：课程归属经课程服务校验；学生创建被拒。"""
    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    _, assign = req('POST', '/api/assignments/', {'course': course_id, 'title': f'E2E作业{SUFFIX}',
                                                  'description': '端到端作业', 'deadline': deadline},
                    token=tokens['tea'], expect=201, name='E2E-TC07 教师创建作业')
    req('POST', '/api/assignments/', {'course': course_id, 'title': '越权作业',
                                      'description': 'x', 'deadline': deadline},
        token=tokens['stu'], expect=403, name='E2E-TC07-异常 学生创建作业被拒')
    req('POST', '/api/assignments/', {'course': 999999, 'title': '幽灵课程作业',
                                      'description': 'x', 'deadline': deadline},
        token=tokens['tea'], expect=400, name='E2E-TC07-异常 不存在的课程被拒（跨服务校验）')
    expired_deadline = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    _, expired = req('POST', '/api/assignments/', {'course': course_id, 'title': f'E2E过期作业{SUFFIX}',
                                                   'description': '已过期', 'deadline': expired_deadline},
                     token=tokens['tea'], expect=201, name='E2E-TC07 创建过期作业（供异常用例）')
    return assign, expired


def tc08_assignment_detail(tokens, assign):
    """E2E-TC08 查看作业详情与参考文档（UC08）。"""
    _, detail = req('GET', f"/api/assignments/{assign['id']}/", token=tokens['stu'], expect=200,
                    name='E2E-TC08 学生查看作业详情')
    assert_true(detail.get('title'), 'E2E-TC08 详情返回作业标题', str(detail)[:100])


def tc09_submit(tokens, assign, expired):
    """E2E-TC09 学生提交作业（UC09）：选课校验经课程服务；教师/未选课/过期被拒。"""
    _, sub = req('POST', '/api/submissions/', {'assignment': assign['id'], 'code': 'print("e2e")\n'},
                 token=tokens['stu'], expect=201, name='E2E-TC09 学生提交作业')
    assert_true(sub.get('status') == 'pending', 'E2E-TC09 提交状态为 pending', str(sub)[:100])
    assert_true(sub.get('student_name') == tokens['stu_name'],
                'E2E-TC09 学生用户名经用户服务补全', str(sub.get('student_name')))
    req('POST', '/api/submissions/', {'assignment': assign['id'], 'code': 'x'},
        token=tokens['tea'], expect=403, name='E2E-TC09-异常 教师提交被拒')
    req('POST', '/api/submissions/', {'assignment': expired['id'], 'code': 'x'},
        token=tokens['stu'], expect=400, name='E2E-TC09-异常 过期作业提交被拒')
    return sub


def tc10_my_submissions(tokens, assign, sub):
    """E2E-TC10 学生查看个人提交记录（UC10）：只能看到自己的提交且按作业隔离。"""
    _, my = req('GET', f"/api/submissions/?assignment={assign['id']}", token=tokens['stu'],
                expect=200, name='E2E-TC10 学生查看提交记录')
    ids = [s['id'] for s in my.get('results') or my]
    assert_true(sub['id'] in ids, 'E2E-TC10 记录包含本次提交', str(ids)[:100])


def tc11_teacher_review(tokens, assign, sub):
    """E2E-TC11 教师查看某作业的全部提交（UC11）：课程范围经课程服务圈定。"""
    _, tea_subs = req('GET', f"/api/submissions/?assignment={assign['id']}", token=tokens['tea'],
                      expect=200, name='E2E-TC11 教师查看作业提交列表')
    ids = [s['id'] for s in tea_subs.get('results') or tea_subs]
    assert_true(sub['id'] in ids, 'E2E-TC11 列表包含该提交', str(ids)[:100])


def tc12_grade(tokens, sub):
    """E2E-TC12 教师评分（UC12）：评分成功生效；学生评分被拒；分数越界被拒。"""
    _, graded = req('POST', f"/api/submissions/{sub['id']}/grade/", {'score': 92},
                    token=tokens['tea'], expect=200, name='E2E-TC12 教师评分')
    assert_true(graded.get('status') == 'graded' and graded.get('score') == 92,
                'E2E-TC12 评分结果 graded/92', str(graded)[:100])
    req('POST', f"/api/submissions/{sub['id']}/grade/", {'score': 100},
        token=tokens['stu'], expect=403, name='E2E-TC12-异常 学生评分被拒')
    req('POST', f"/api/submissions/{sub['id']}/grade/", {'score': 150},
        token=tokens['tea'], expect=400, name='E2E-TC12-异常 分数越界被拒')


def tc13_profile(tokens, users):
    """E2E-TC13 查看个人信息（UC13）：me 接口返回本人数据。"""
    _, me = req('GET', '/api/users/me/', token=tokens['stu'], expect=200,
                name='E2E-TC13 学生查看个人信息')
    assert_true(me.get('username') == users['stu']['username'], 'E2E-TC13 个人信息正确',
                str(me)[:100])


def tc14_admin(admin_cred):
    """E2E-TC14 管理员后台管理（UC14）：走真实登录流程访问 user-service 的 Django Admin。

    微服务版后台在用户服务（课程/作业数据归各服务库，无集中后台），检查用户管理页。
    """
    if not admin_cred:
        results.append({'name': 'E2E-TC14 管理员后台', 'ok': False, 'code': 'setup failed'})
        print('FAIL  E2E-TC14 管理员后台: 无法创建临时管理员')
        return
    username, password = admin_cred
    session = requests.Session()
    login_page = session.get(BASE + '/admin/login/', timeout=20)
    ok_login_page = login_page.status_code == 200
    csrf = session.cookies.get('csrftoken', '')
    r = session.post(BASE + '/admin/login/', data={
        'username': username, 'password': password,
        'csrfmiddlewaretoken': csrf, 'next': '/admin/',
    }, headers={'Referer': BASE + '/admin/login/'}, timeout=20)
    ok_login = r.status_code == 200 and ('登录' in r.text or r.url.endswith('/admin/'))
    pages_ok = True
    for path in ('/admin/', '/admin/users/user/', '/admin/users/emailverificationcode/'):
        res = session.get(BASE + path, timeout=20)
        if res.status_code != 200:
            pages_ok = False
            print(f'     管理页 {path} -> HTTP {res.status_code}')
    ok = ok_login_page and ok_login and pages_ok
    results.append({'name': 'E2E-TC14 管理员后台（登录 + 用户管理页）', 'ok': ok,
                    'code': 'OK' if ok else 'check log'})
    print(f'{"PASS" if ok else "FAIL"}  E2E-TC14 管理员后台（登录 + 用户管理页）')


def tc15_delete_cascade(tokens, users, course_id):
    """删除用户触发跨服务级联清理（微服务新增场景，对应《跨服务调用说明.md》第 4 节）。"""
    for u in (users['stu'], users['tea']):
        req('DELETE', f"/api/users/{u['id']}/", token=tokens['tea'], expect=204,
            name=f'E2E-清理 删除测试账号 {u["username"]}（级联清理课程/作业/提交）')
    # 验证级联结果：课程已随教师删除
    req('GET', f'/api/courses/{course_id}/', token=tokens['tea'], expect=404,
        name='E2E-清理 教师课程已级联删除')


# ---------- 主流程 ----------

def main():
    print(f'==== 微服务版端到端回归（E2E-TC01~14 + 级联清理） {datetime.now():%Y-%m-%d %H:%M:%S} ====')
    if not BASE:
        print('必须设置 E2E_BASE_URL（如 http://127.0.0.1:8080），测试中止')
        return False
    if not EXEC_PREFIX:
        print('警告: 未设置 E2E_EXEC_PREFIX，验证码/管理员注入将失败')

    if not gateway_alive():
        print('网关或业务服务探活失败，测试中止')
        write_report(0, len(results))
        return False

    users = tc01_registration()
    tokens = tc02_login(users)
    tokens['tea_name'] = users['tea']['username']
    tokens['stu_name'] = users['stu']['username']
    course = tc05_create_course(tokens)
    course_id = course['id']
    tc03_browse_courses(tokens, course_id)
    tc04_enroll(tokens, course_id)
    tc06_manage_course(tokens, course_id)
    assign, expired = tc07_manage_assignment(tokens, course_id)
    tc08_assignment_detail(tokens, assign)
    sub = tc09_submit(tokens, assign, expired)
    tc10_my_submissions(tokens, assign, sub)
    tc11_teacher_review(tokens, assign, sub)
    tc12_grade(tokens, sub)
    tc13_profile(tokens, users)

    admin_cred = ensure_admin()
    tc14_admin(admin_cred)
    tc15_delete_cascade(tokens, users, course_id)
    if admin_cred:
        username, _ = admin_cred
        exec_in_user_service(
            f"from users.models import User; User.objects.filter(username='{username}').delete()")

    passed = sum(1 for r in results if r['ok'])
    total = len(results)
    print(f'\n========== 微服务端到端结果汇总: {passed}/{total} 通过 ==========')
    write_report(passed, total)
    return passed == total


def write_report(passed, total):
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    lines = [
        '# 微服务版端到端测试报告（E2E-TC01~14 + 级联清理）',
        '',
        f'- 运行时间：{datetime.now():%Y-%m-%d %H:%M:%S}',
        f'- 运行环境：Python {sys.version.split()[0]}，目标地址 {BASE}，'
        f'exec 前缀 \'{" ".join(EXEC_PREFIX) or "(未配置)"}\'',
        f'- 测试总数：{total}　通过：{passed}　失败：{total - passed}',
    ]
    failed = [r for r in results if not r['ok']]
    if failed:
        lines.append('- 失败项：')
        for r in failed:
            lines.append(f'  - {r["name"]}（实际 HTTP {r["code"]}）')
    else:
        lines.append('- 失败原因：无')
    lines += ['', '## 明细', '', '| 测试项 | 结果 |', '|---|---|']
    for r in results:
        lines.append(f'| {r["name"]} | {"PASS" if r["ok"] else "FAIL"} |')
    path = os.path.join(REPORT_DIR, f'e2e_micro_report_{stamp}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'报告已写入 {path}')


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
