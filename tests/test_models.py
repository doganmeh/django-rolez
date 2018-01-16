from django.contrib.auth.models import Permission, Group
from django.db import IntegrityError
from django.test import TestCase as ModelTestCase  # use when querying models
from unittest import TestCase as NonModelTestCase  # use otherwise
from tests.test_app.models import Author, Blog
from rolez.models import Role
from rolez.backend import RolePermissionBackend
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

UserModel = get_user_model()


# assert list: https://docs.python.org/3/library/unittest.html#assert-methods:

# Method						Checks that
# assertNotEqual(a, b)			a != b
# assertTrue(x)					bool(x) is True
# assertFalse(x)				bool(x) is False
# assertIs(a, b)				a is b
# assertIsNot(a, b)				a is not b
# assertIsNone(x)				x is None
# assertIn(a, b)				a in b
# assertNotIn(a, b)				a not in b
# assertIsInstance(a, b)		isinstance(a, b)
# assertNotIsInstance(a, b)		not isinstance(a, b)

# django specific: https://docs.djangoproject.com/en/dev/topics/testing/tools/#assertions

# testing views: https://docs.djangoproject.com/en/dev/intro/tutorial05/#the-django-test-client


class RoleTests(ModelTestCase):
	def setUp(self):
		self.brandon = UserModel.objects.create(username='brandon')
		self.jack = UserModel.objects.create(username='jack')

		self.admins_group = Group.objects.create(name='admins') # author add, change, delete
		self.users_group = Group.objects.create(name='users')

		self.editor_role = Role.objects.create(name='editor') # blog change
		self.author_role = Role.objects.create(name='author') # blog change, add

		self.jack.groups.add(self.users_group)
		self.brandon.groups.add(self.admins_group)

		self.backend = RolePermissionBackend()

	def test_create_delete_role(self):
		role = Role.objects.create (name="Maintenance")
		self.assertIsNotNone(role.delegate)

		ctype = ContentType.objects.get_for_model(role)  # takes obj or model
		delegate = Permission.objects.filter(content_type=ctype, codename=role.codename())
		self.assertEqual(list(delegate).__len__(), 1)  # delegate created

		role.delete()
		delegate = Permission.objects.filter(content_type=ctype, codename=role.codename())
		self.assertEqual(list(delegate).__len__(), 0)  # delegate also deleted

	def test_create_duplicate_role(self):
		role = Role(name="Admin")
		role.save()
		role = Role(name="Admin")
		with self.assertRaises(IntegrityError):
			role.save()

	def test_user_regular_perm(self):
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_author'), False)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.add_author'), False)

		content_type = ContentType.objects.get_for_model(Author)
		add_author = Permission.objects.get(content_type=content_type, codename='add_author')
		self.jack.user_permissions.add(add_author)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_author'), False)

	def test_user_role_perm(self):
		content_type = ContentType.objects.get_for_model(Author)
		add_author = Permission.objects.get(content_type=content_type, codename='add_author')
		role = Role.objects.create (name="Maintenance")
		role.perms.add(add_author)
		self.jack.user_permissions.add(role.delegate)
		self.assertIs(self.jack.has_perm('rolez.use_role_maintenance'), True)

		self.backend.clear_cache(self.jack)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_author'), True)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.add_author'), False)

	def test_group_regular_perm(self):
		self.assertEqual(self.jack.groups.all().__len__(), 1)
		self.assertEqual(self.brandon.groups.all().__len__(), 1)

		content_type = ContentType.objects.get_for_model(Author)
		delete_author = Permission.objects.get(content_type=content_type, codename='delete_author')
		self.admins_group.permissions.add(delete_author)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.delete_author'), False)

	def test_group_role_perm(self):
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), False)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)

		content_type = ContentType.objects.get_for_model(Blog)
		change_blog = Permission.objects.get(content_type=content_type, codename='change_blog')
		add_blog = Permission.objects.get(content_type=content_type, codename='add_blog')

		self.editor_role.perms.add(change_blog)
		self.author_role.perms.add(change_blog, add_blog)

		self.users_group.permissions.add(self.editor_role.delegate) # all users have editor role

		self.backend.clear_cache(self.jack)
		self.backend.clear_cache(self.brandon)

		self.assertIs(self.jack.has_perm('rolez.use_role_editor'), True)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), True)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)

		self.assertIs(self.brandon.has_perm('rolez.use_role_editor'), False)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_blog'), False)


