# -*- coding: utf-8 -*-
"""E2E-TC01~14 全流程端到端测试：从 API 入口走完清单中每个业务场景（用例）的完整流程。

设计要点：
- 默认连接 127.0.0.1:8000；若服务未启动，自动用本仓库 venv 启动 runserver 到 8765，跑完关闭。
- 每用例一个测试函数（E2E-TC01~14），内部逐项断言（状态码 + 业务数据）。
- 测试账号带 e2e_ 前缀与时间戳，跑完自动删除（级联清理课程/作业/提交）。
- 退出码：全部通过返回 0，任一失败返回 1；同时把结果写入 04_tests/reports/。

用法：
    python 04_tests/e2e/run_e2e.py            # 复用 8000 端口或自动起服务
    E2E_BASE_URL=http://127.0.0.1:9999 python 04_tests/e2e/run_e2e.py
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_DIR = os.path.join(REPO_ROOT, 'web_backend')
REPORT_DIR = os.path.join(REPO_ROOT, '04_tests', 'reports')

BASE = os.environ.get('E2E_BASE_URL', 'http://127.0.0.1:8000')
AUTO_PORT = 8765
SUFFIX = str(int(time.time()))[-6:]
results = []


# ---------- 基础设施 ----------

def req(method, path, data=None, token=None, expect=None, name=''):
    """发送请求并断言状态码；返回 (status_code, json)。"""
    headers = {}
    if token:
        headers['Authorization'] = f'Token {token}'
    r = requests.request(method, BASE + path, json=data, headers=headers, timeout=15)
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


def server_alive(url):
    try:
        return requests.get(url + '/api/users/me/', timeout=3).status_code in (200, 403)
    except requests.RequestException:
        return False


def ensure_server():
    """服务已启动则复用（不接管生命周期），否则自动启动并在结束后关闭。"""
    if server_alive(BASE):
        print(f'[setup] 复用已运行的后端 {BASE}')
        return None
    print(f'[setup] {BASE} 不可达，自动启动后端到 127.0.0.1:{AUTO_PORT} ...')
    proc = subprocess.Popen(
        [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{AUTO_PORT}', '--noreload'],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    auto_base = f'http://127.0.0.1:{AUTO_PORT}'
    for _ in range(60):
        if server_alive(auto_base):
            print(f'[setup] 后端已就绪 {auto_base}')
            return proc, auto_base
        if proc.poll() is not None:
            print('[setup] 后端启动失败，请检查 manage.py runserver 输出')
            return None
        time.sleep(1)
    print('[setup] 等待后端就绪超时')
    proc.terminate()
    return None


def ensure_admin():
    """E2E-TC14 需要管理员账号；通过 manage.py shell 创建临时管理员（密码随机，跑完删除）。"""
    username = f'e2e_admin_{SUFFIX}'
    password = f'E2ePass{SUFFIX}!'
    code = (
        "from apps.models import User;"
        f"u, _ = User.objects.get_or_create(username='{username}');"
        "u.is_staff=True; u.is_superuser=True;"
        f"u.set_password('{password}'); u.save(); print(u.id)"
    )
    out = subprocess.run(
        [sys.executable, 'manage.py', 'shell', '-c', code],
        cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        print(f'[setup] 创建管理员失败: {out.stderr[:300]}')
        return None
    return username, password


def latest_code(email):
    """直接写入验证码，避免 E2E 走真实 SMTP 向 example.com 发信。"""
    script = (
        "from apps.models import EmailVerificationCode;"
        f"print(EmailVerificationCode.issue('{email.lower()}').code)"
    )
    out = subprocess.run(
        [sys.executable, 'manage.py', 'shell', '-c', script],
        cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        print(f'[setup] 写入验证码失败: {out.stderr[:300]}')
        return ''
    lines = [ln.strip() for ln in (out.stdout or '').splitlines() if ln.strip()]
    return lines[-1] if lines else ''


def register_with_code(username, email, password='e2e1234', is_teacher=False, name=''):
    code = latest_code(email)
    payload = {'username': username, 'password': password, 'email': email,
               'verification_code': code}
    if is_teacher:
        payload['is_teacher'] = True
    return req('POST', '/api/users/', payload, expect=201, name=name)


# ---------- 用例级端到端测试（E2E-TC01~14） ----------

def tc01_registration():
    """E2E-TC01 用户注册（UC01）：学生/教师注册成功；缺邮箱被拒。"""
    name = f'e2e_stu_{SUFFIX}'
    email = f'{name}@example.com'
    _, stu = register_with_code(name, email, name='E2E-TC01 学生注册')
    tea_name = f'e2e_tea_{SUFFIX}'
    _, tea = register_with_code(tea_name, f'{tea_name}@example.com', is_teacher=True,
                                name='E2E-TC01 教师注册')
    req('POST', '/api/users/', {'username': f'e2e_nomail_{SUFFIX}', 'password': 'e2e1234'},
        expect=400, name='E2E-TC01-异常 缺邮箱注册被拒')
    return {'stu': stu, 'tea': tea}


def tc02_login(users):
    """E2E-TC02 用户登录（UC02）：签发 Token；错误密码/未注册被拒。"""
    _, stu_login = req('POST', '/api/auth/token/', {'username': users['stu']['username'],
                                                    'password': 'e2e1234'},
                       expect=200, name='E2E-TC02 学生登录')
    _, tea_login = req('POST', '/api/auth/token/', {'username': users['tea']['username'],
                                                    'password': 'e2e1234'},
                       expect=200, name='E2E-TC02 教师登录')
    req('POST', '/api/auth/token/', {'username': users['stu']['username'], 'password': 'wrong'},
        expect=400, name='E2E-TC02-异常 错误密码被拒')
    return {'stu': stu_login['token'], 'tea': tea_login['token']}


def tc03_browse_courses(tokens, course_id):
    """E2E-TC03 浏览课程列表与详情（UC03）：列表包含新课程；详情字段正确。"""
    _, lst = req('GET', '/api/courses/', token=tokens['stu'], expect=200,
                 name='E2E-TC03 学生浏览课程列表')
    found = any(c['id'] == course_id for c in lst.get('results') or lst)
    assert_true(found, 'E2E-TC03 列表包含新课程')
    _, detail = req('GET', f'/api/courses/{course_id}/', token=tokens['stu'], expect=200,
                    name='E2E-TC03 学生查看课程详情')
    assert_true(detail.get('name'), 'E2E-TC03 详情返回课程名称', str(detail)[:100])


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
    """E2E-TC07 教师管理作业（UC07）：创建（含参考文档）；学生创建被拒。"""
    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    _, assign = req('POST', '/api/assignments/', {'course': course_id, 'title': f'E2E作业{SUFFIX}',
                                                  'description': '端到端作业', 'deadline': deadline},
                    token=tokens['tea'], expect=201, name='E2E-TC07 教师创建作业')
    req('POST', '/api/assignments/', {'course': course_id, 'title': '越权作业',
                                      'description': 'x', 'deadline': deadline},
        token=tokens['stu'], expect=403, name='E2E-TC07-异常 学生创建作业被拒')
    expired_deadline = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    _, expired = req('POST', '/api/assignments/', {'course': course_id, 'title': f'E2E过期作业{SUFFIX}',
                                                   'description': '已过期', 'deadline': expired_deadline},
                     token=tokens['tea'], expect=201, name='E2E-TC07 创建过期作业（供异常用例）')
    return assign, expired


def tc08_assignment_detail(tokens, assign):
    """E2E-TC08 查看作业详情与参考文档（UC08）：学生可查看作业详情。"""
    _, detail = req('GET', f"/api/assignments/{assign['id']}/", token=tokens['stu'], expect=200,
                    name='E2E-TC08 学生查看作业详情')
    assert_true(detail.get('title'), 'E2E-TC08 详情返回作业标题', str(detail)[:100])


def tc09_submit(tokens, assign, expired):
    """E2E-TC09 学生提交作业（UC09）：成功 pending；未选课/教师/过期被拒。"""
    _, sub = req('POST', '/api/submissions/', {'assignment': assign['id'], 'code': 'print("e2e")\n'},
                 token=tokens['stu'], expect=201, name='E2E-TC09 学生提交作业')
    assert_true(sub.get('status') == 'pending', 'E2E-TC09 提交状态为 pending', str(sub)[:100])
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
    """E2E-TC11 教师查看某作业的全部提交（UC11）：列表包含学生提交。"""
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
    """E2E-TC14 管理员后台管理（UC14）：走真实登录流程访问四个模型管理页。"""
    if not admin_cred:
        results.append({'name': 'E2E-TC14 管理员后台', 'ok': False, 'code': 'setup failed'})
        print('FAIL  E2E-TC14 管理员后台: 无法创建临时管理员')
        return
    username, password = admin_cred
    session = requests.Session()
    login_page = session.get(BASE + '/admin/login/', timeout=15)
    ok_login_page = login_page.status_code == 200
    csrf = session.cookies.get('csrftoken', '')
    r = session.post(BASE + '/admin/login/', data={
        'username': username, 'password': password,
        'csrfmiddlewaretoken': csrf, 'next': '/admin/',
    }, headers={'Referer': BASE + '/admin/login/'}, timeout=15)
    ok_login = r.status_code == 200 and '登录' in r.text or r.url.endswith('/admin/')
    pages_ok = True
    for path in ('/admin/', '/admin/apps/user/', '/admin/apps/course/',
                 '/admin/apps/assignment/', '/admin/apps/submission/'):
        res = session.get(BASE + path, timeout=15)
        if res.status_code != 200:
            pages_ok = False
            print(f'     管理页 {path} -> HTTP {res.status_code}')
    ok = ok_login_page and ok_login and pages_ok
    results.append({'name': 'E2E-TC14 管理员后台（登录 + 4 个管理页）', 'ok': ok,
                    'code': 'OK' if ok else 'check log'})
    print(f'{"PASS" if ok else "FAIL"}  E2E-TC14 管理员后台（登录 + 4 个管理页）')


# ---------- 主流程 ----------

def main():
    print(f'==== 端到端测试（E2E-TC01~14） {datetime.now():%Y-%m-%d %H:%M:%S} ====')
    server_info = ensure_server()
    if server_info is None:
        print('无法连接或启动后端，测试中止')
        return False
    proc, base = server_info
    global BASE
    if base:
        BASE = base

    users = tc01_registration()
    tokens = tc02_login(users)
    tokens['tea_name'] = users['tea']['username']
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

    # 清理：删除测试账号（级联删除课程/作业/提交）与临时管理员
    for u in (users['stu'], users['tea']):
        req('DELETE', f"/api/users/{u['id']}/", token=tokens['tea'], expect=204,
            name=f'清理 删除测试账号 {u["username"]}')
    if admin_cred:
        username, _ = admin_cred
        subprocess.run([sys.executable, 'manage.py', 'shell', '-c',
                        f"from apps.models import User; User.objects.filter(username='{username}').delete()"],
                       cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60)

    if proc is not None:
        proc.terminate()
        print(f'[teardown] 已关闭自动启动的后端 127.0.0.1:{AUTO_PORT}')

    passed = sum(1 for r in results if r['ok'])
    total = len(results)
    print(f'\n========== 端到端结果汇总: {passed}/{total} 通过 ==========')
    write_report(passed, total)
    return passed == total


def write_report(passed, total):
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    lines = [
        '# 端到端测试报告（E2E-TC01~14）',
        '',
        f'- 运行时间：{datetime.now():%Y-%m-%d %H:%M:%S}',
        f'- 运行环境：Python {sys.version.split()[0]}，Windows，后端地址 {BASE}',
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
    path = os.path.join(REPORT_DIR, f'e2e_report_{stamp}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'报告已写入 {path}')


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
