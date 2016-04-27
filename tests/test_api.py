import unittest, json, re
from base64 import b64encode
from flask import url_for
from app import create_app, db
from app.models import Role, User, Post, Comment


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_contest = self.app.app_context()
        self.app_contest.push()
        db.create_all()
        Role.insert_roles()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_contest.pop()

    def get_api_headers(self, username, password):
        return {
            'Authorization': 'Basic ' + b64encode((username + ':' + password).encode('utf-8')).decode('utf-8'),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def test_404(self):
        response = self.client.get('/wrong/url', headers=self.get_api_headers('emali','password'))
        self.assertTrue(response.status_code == 404)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['error'] == 'not found')

    def test_bad_auth(self):
        # 添加一个用户
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=True, role=r)
        db.session.add(u)
        db.session.commit()

        # 密码错误认证
        response = self.client.get(url_for('api.get_posts'), headers=self.get_api_headers('john@example.com', 'dog'))
        self.assertTrue(response.status_code == 401)

    def test_token_auth(self):
        # 添加一个用户
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=True, role=r)
        db.session.add(u)
        db.session.commit()

        # 错误token请求
        response = self.client.get(url_for('api.get_posts'), headers=self.get_api_headers('bad-token', ''))
        self.assertTrue(response.status_code == 401)

        # 获取token
        response = self.client.get(url_for('api.get_token'), headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(json_response.get('token'))
        token = json_response.get('token')

        # 使用token请求
        response = self.client.get(url_for('api.get_posts'), headers=self.get_api_headers(token, ''))
        self.assertTrue(response.status_code == 200)

    def test_anonymous(self):
        response = self.client.get(url_for('api.get_posts'), headers=self.get_api_headers('', ''))
        self.assertTrue(response.status_code == 200)

    def test_unconfirmed_account(self):
        # 添加一个未确认用户
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=False, role=r)
        db.session.add(u)
        db.session.commit()

        # 未确认用户获取博客
        response = self.client.get(url_for('api.get_posts'), headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 403)

    def test_no_auth(self):
        response = self.client.get(url_for('api.get_posts'), content_type='application/json')
        self.assertTrue(response.status_code == 200)

    def test_posts(self):
        # 添加一个用户
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u = User(email='john@example.com', password='cat', confirmed=True, role=r)
        db.session.add(u)
        db.session.commit()

        # 写一篇空博客
        response = self.client.post(url_for('api.new_post'), headers=self.get_api_headers('john@example.com', 'cat'),
                                    data=json.dumps({'body': ''}))
        self.assertTrue(response.status_code == 400)

        # 写一篇文章
        response = self.client.post(url_for('api.new_post'), headers=self.get_api_headers('john@example.com', 'cat'),
                                    data=json.dumps({'body': 'body of the *blog* post'}))
        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIsNotNone(url)

        # 获取刚发布的文章
        response = self.client.get(url, headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['url'] == url)
        self.assertTrue(json_response['body'] == 'body of the *blog* post')
        self.assertTrue(json_response['body_html'] == '<p>body of the <em>blog</em> post</p>')
        json_post = json_response

        # 获取用户的博客
        response = self.client.get(url_for('api.get_user_posts', id=u.id),
                                   headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(json_response.get('posts'))
        self.assertTrue(json_response.get('count', 0) == 1)
        self.assertTrue(json_response['posts'][0] == json_post)

        # 获取关注者的博客
        response = self.client.get(url_for('api.get_user_followed_posts', id=u.id),
                                   headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(json_response.get('posts'))
        self.assertTrue(json_response.get('count') == 1)
        self.assertTrue(json_response['posts'][0] == json_post)

        # 编辑博客
        post = Post.query.filter_by(body=json_post.get('body')).first()
        response = self.client.post(url_for('api.edit_post', id=post.id),
                                    # 本书源码是put(url,headers,data)，测试报错，修改成这样，还是报错，原因不明
                                    headers=self.get_api_headers('john@example.com', 'cat'),
                                    data=json.dumps({'body': 'updated body'}))
        self.assertTrue(response.status_code == 201)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['url'] == url)
        self.assertTrue(json_response['body'] == 'updated body')
        self.assertTrue(json_response['body_html'] == '<p>updated body</p>')

    def test_user(self):
        # 添加两个用户
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u1 = User(email='john@example.com', password='cat', username='john', confirmed=True, role=r)
        u2 = User(email='susan@example.com', password='dog', username='susan', confirmed=True, role=r)
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        # 获取用户
        response = self.client.get(url_for('api.get_user', id=u2.id),
                                   headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['username'] == 'susan')
        response = self.client.get(url_for('api.get_user', id=u1.id),
                                   headers=self.get_api_headers('susan@example.com', 'dog'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['username'] == 'john')

    def test_comments(self):
        # 添加两个用户
        r = Role.query.filter_by(name='User').first()
        self.assertIsNotNone(r)
        u1 = User(email='john@example.com', password='cat', username='john', confirmed=True, role=r)
        u2 = User(email='susan@example.com', password='dog', username='susan', confirmed=True, role=r)
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        # 添加一篇博客
        post = Post(body='body of the post', author=u1)
        db.session.add(post)
        db.session.commit()

        # write a comment
        response = self.client.post(
            url_for('api.new_post_comment', id=post.id),
            headers=self.get_api_headers('susan@example.com', 'dog'),
            data=json.dumps({'body': 'Good [post](http://example.com)!'}))
        # 测试失败，原因不明
        self.assertTrue(response.status_code == 201)
        json_response = json.loads(response.data.decode('utf-8'))
        url = response.headers.get('Location')
        self.assertIsNotNone(url)
        self.assertTrue(json_response['body'] ==
                        'Good [post](http://example.com)!')
        self.assertTrue(
            re.sub('<.*?>', '', json_response['body_html']) == 'Good post!')

        # 获取一条评论
        response = self.client.get(url, headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertTrue(json_response['url'] == url)
        self.assertTrue(json_response['body'] == 'Good [post] (http://example.com)!')

        # 再添加一条评论
        comment = Comment(body='Thank you!', author=u1, post=post)
        db.session.add(comment)
        db.session.commit()

        # 从博客中获取两条评论
        response = self.client.get(url_for('api.get_post_comments', id=post.id),
                                   headers=self.get_api_headers('susan@example.com', 'dog'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(json_response.get('post'))
        self.assertTrue(json_response.get('count') == 2)

        #  获取所有评论
        response = self.client.get(url_for('api.get_comments'), headers=self.get_api_headers('john@example.com', 'cat'))
        self.assertTrue(response.status_code == 200)
        json_response = json.loads(response.data.decode('utf-8'))
        self.assertIsNone(json_response.get('posts'))
        self.assertTrue(json_response.get('count', 0) == 1)
