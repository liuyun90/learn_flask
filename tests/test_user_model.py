
import unittest
import time
from app.models import User, Role, Permission, AnonymousUser, Follow
from app import db, create_app
'''单元测试的数据库如果是开发数据库，测试时，如果第一次测试的数据已经写入数据库，第二次测试有相同的数据
要写入数据库时，可能报错'''


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        # 创建App时输入config作为参数，将单元测试放在测试环境下进行，db链接的是测试数据库
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_setter(self):
        u = User(password = 'cat')
        self.assertTrue(u.password_hash is not None)

    def test_no_password_getter(self):
        u = User(password = 'cat')
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self):
        u = User(password = 'cat')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))

    def test_password_salts_are_random(self):
        u = User(password = 'cat')
        u2 = User(password = 'cat')
        self.assertFalse(u.password_hash == u2.password_hash)

    def test_valid_confirmation_token(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token()
        self.assertTrue(u.confirm(token))

    def test_invalid_confirmation_token(self):
        u1 = User(password='cat')
        u2 = User(password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_confirmation_token()
        self.assertFalse(u2.confirm(token))

    def test_expired_confirmation_token(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token(1)
        time.sleep(2)
        self.assertFalse(u.confirm(token))

    def test_valid_reset_token(self):
        u = User(password = 'cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_reset_token()
        self.assertTrue(u.reset_password(token, 'dog'))
        self.assertTrue(u.verify_password('dog'))

    def test_invalid_reset_token(self):
        u1 = User(password='cat')
        u2 = User(password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_reset_token()
        self.assertFalse(u2.reset_password(token, 'horse'))
        self.assertTrue(u2.verify_password('dog'))

    def test_valid_email_change_token(self):
        u = User(password='cat')
        db.session.add(u)
        db.session.commit()
        token = u.generate_email_change_token('susan@example.com')
        self.assertTrue(u.change_email(token))
        self.assertTrue(u.email=='susan@example.com')

    def test_invalid_email_change_token(self):
        u1 = User(email='john1@example.com',password='cat')
        u2 = User(email='susan1@example.org',password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_email_change_token('david@example.net')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'susan1@example.org')

    def test_duplicate_email_change_token(self):
        u1 = User(email='john2@example.com', password='cat')
        u2 = User(email='susan2@example.org', password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u2.generate_email_change_token('john2@example.com')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'susan2@example.org')

    def test_roles_and_permissions(self):
        u = User(email = 'john5@example.com', password='cat')
        self.assertTrue(u.can(Permission.WRITE_ARTICLES))
        self.assertFalse(u.can(Permission.MODERATE_COMMENTS))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.FOLLOW))

    def test_follow(self):
        u1 = User(email='john@example.com', password='cat')
        u2 = User(email='susan@example.com', password='dog')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertFalse(u1.is_followed_by(u2))
        u1.follow(u2)
        db.session.add(u1)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertFalse(u1.is_followed_by(u2))
        self.assertTrue(u2.is_followed_by(u1))
        self.assertFalse(u2.is_following(u1))
        self.assertTrue(u1.followed.count() == 2)
        self.assertTrue(u2.followers.count() == 2)
        f = u2.followers.order_by(Follow.timestamp.desc()).all()[0]
        self.assertTrue(f.follower == u1)
        u1.unfollow(u2)
        db.session.add(u1)
        db.session.commit()
        self.assertTrue(u1.followed.count() == 1)
        self.assertTrue(u2.followers.count() == 1)
        self.assertTrue(Follow.query.count() == 2)
        u2.follow(u1)
        db.session.add(u2)
        db.session.add(u1)
        db.session.commit()
        db.session.delete(u2)
        db.session.commit()
        self.assertTrue(Follow.query.count() == 1)
