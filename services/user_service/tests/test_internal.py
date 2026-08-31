"""用户服务内部接口测试（供 course/assignment 服务调用的契约）。"""
from django.test import TestCase

from .helpers import create_user

INTERNAL = '/internal/users/'


class InternalUserApiTests(TestCase):
    def setUp(self):
        self.s1 = create_user('u1', email='u1@example.com')
        self.t1 = create_user('t1', is_teacher=True, email='t1@example.com')

    def _hdr(self):
        return {'HTTP_X_INTERNAL_KEY': 'dev-internal-key'}

    def test_batch_by_ids(self):
        resp = self.client.get(INTERNAL, {'ids': f'{self.s1.id},{self.t1.id}'}, **self._hdr())
        self.assertEqual(resp.status_code, 200)
        ids = [u['id'] for u in resp.json()]
        self.assertCountEqual(ids, [self.s1.id, self.t1.id])
        usernames = {u['id']: u['username'] for u in resp.json()}
        self.assertEqual(usernames[self.t1.id], 't1')
        self.assertTrue([u for u in resp.json() if u['id'] == self.t1.id][0]['is_teacher'])

    def test_lookup_by_username(self):
        resp = self.client.get(INTERNAL, {'username': 't1'}, **self._hdr())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()[0]['id'], self.t1.id)

    def test_wrong_internal_key_forbidden(self):
        resp = self.client.get(INTERNAL, {'ids': '1'}, HTTP_X_INTERNAL_KEY='bad')
        self.assertEqual(resp.status_code, 403)

    def test_missing_key_forbidden(self):
        resp = self.client.get(INTERNAL, {'ids': '1'})
        self.assertEqual(resp.status_code, 403)

    def test_missing_params_rejected(self):
        resp = self.client.get(INTERNAL, **self._hdr())
        self.assertEqual(resp.status_code, 400)

    def test_bad_ids_rejected(self):
        resp = self.client.get(INTERNAL, {'ids': 'abc'}, **self._hdr())
        self.assertEqual(resp.status_code, 400)
