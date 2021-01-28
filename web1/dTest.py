from django.test import TestCase, client
from ApiManager.utils import auth
from ApiManager.models import UserInfo
class LoginTest(TestCase):
    def setUp(self):
        UserInfo.objects.create(create_time='2019-08-16 15:07:56.244794', update_time='2019-08-16 15:07:56.244794', username='test', password='111111', email="zlinghu@126.com", status=1)
        print("test case start!")

    def test_log_url(self):
        c = client.Client()
        resp = c.post('/api/login/', {"account": "test", "password": "111111"}, follow=True)
        self.assertContains(resp, "test")

    def test_auth(self):
        ret = auth.auth_user("linghu.zeng@united-imaging.com", "Welcome2uih6")
        self.assertEqual(ret, 1, "Test passed!")

    def tearDown(self):
        print("test case end!")




