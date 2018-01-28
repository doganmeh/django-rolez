from django.contrib.auth.models import Permission, Group
from django.db import IntegrityError
from django.test import TestCase as ModelTestCase, override_settings  # use when querying models
from unittest import TestCase as NonModelTestCase  # use otherwise
from tests.test_app.models import Author, Blog
from rolez.models import Role
from rolez.backend import RoleModelBackend, RoleModelObjectBackend
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from guardian.shortcuts import assign_perm

UserModel = get_user_model()


# assert list: https://docs.python.org/3/library/unittest.html#assert-methods:
# or use code completion: self.assert ...

# django specific: https://docs.djangoproject.com/en/dev/topics/testing/tools/#assertions

# testing views: https://docs.djangoproject.com/en/dev/intro/tutorial05/#the-django-test-client

@override_settings(
    AUTHENTICATION_BACKENDS=[
		  'django.contrib.auth.backends.ModelBackend',
		  'rolez.backend.RoleModelBackend',
		  ],
)
class ModelTests(ModelTestCase):
	def test_create_delete_role(self):
		role = Role.objects.create (name="Maintenance")
		self.assertIsNotNone(role.delegate)

		ctype = ContentType.objects.get_for_model(role)  # takes obj or model
		delegate = Permission.objects.filter(content_type=ctype, codename=role.codename())
		self.assertEqual(list(delegate).__len__(), 1)  # delegate perm is created

		role.delete()
		delegate = Permission.objects.filter(content_type=ctype, codename=role.codename())
		self.assertEqual(list(delegate).__len__(), 0)  # delegate also deleted

	def test_create_duplicate_role(self):
		role = Role(name="Maintenance")
		role.save()
		role = Role(name="Maintenance")
		with self.assertRaises(IntegrityError):
			role.save()


class BackendTestsCommon(object):
	def setUp(self):
		self.brandon = UserModel.objects.create(username='brandon')
		self.jack = UserModel.objects.create(username='jack')

		self.admins_group = Group.objects.create(name='admins')
		self.users_group = Group.objects.create(name='users')

		self.manager_role = Role.objects.create(name='manager')  # author add, change, delete
		self.editor_role = Role.objects.create(name='editor')  # blog change
		self.author_role = Role.objects.create(name='author')  # blog change, add

		self.jack.groups.add(self.users_group)
		self.brandon.groups.add(self.admins_group)

		content_type = ContentType.objects.get_for_model(Author)
		self.change_author = Permission.objects.get(content_type=content_type, codename='change_author')
		self.delete_author = Permission.objects.get(content_type=content_type, codename='delete_author')

		content_type = ContentType.objects.get_for_model(Blog)
		self.change_blog = Permission.objects.get(content_type=content_type, codename='change_blog')
		self.add_blog = Permission.objects.get(content_type=content_type, codename='add_blog')

		self.manager_role.perms.add(self.change_author, self.delete_author)
		self.editor_role.perms.add(self.change_blog)
		self.author_role.perms.add(self.change_blog, self.add_blog)

		self.twain = Author.objects.create(name="twain")
		self.twain_blog = Blog.objects.create(name="twain personal blog")


	def test_user_deny_non_role_perm(self):
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author'), False)

		# will approve perms in roles only
		self.brandon.user_permissions.add(self.change_author)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author'), False)

	def test_user_role_perm(self):
		self.brandon.user_permissions.add(self.manager_role.delegate)
		self.assertIs(self.brandon.has_perm('rolez.use_role_manager'), True)  # default backend

		self.backend.clear_cache(self.brandon)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author'), True)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_author'), False)

	def test_group_deny_non_role_perm(self):
		self.assertEqual(self.jack.groups.all().__len__(), 1)
		self.assertEqual(self.brandon.groups.all().__len__(), 1)

		# will approve perms in roles only
		self.admins_group.permissions.add(self.delete_author)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.delete_author'), False)

	def test_group_role_perm(self):
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), False)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)

		self.users_group.permissions.add(self.editor_role.delegate) # all users have editor role

		self.backend.clear_cache(self.jack)
		self.backend.clear_cache(self.brandon)

		self.assertIs(self.jack.has_perm('rolez.use_role_editor'), True)  # default backend
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), True)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False) # not author

		self.assertIs(self.brandon.has_perm('rolez.use_role_editor'), False)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_blog'), False)


@override_settings(
    AUTHENTICATION_BACKENDS=[
		  'django.contrib.auth.backends.ModelBackend',
		  'rolez.backend.RoleModelBackend',
		  ],
)
class RoleModelBackendTests(BackendTestsCommon, ModelTestCase):
	def setUp(self):
		super().setUp()
		self.backend = RoleModelBackend()

	def test_get_all_permissions(self):
		self.assertEqual(self.backend.get_all_permissions(self.brandon), set())

		self.admins_group.permissions.add(self.manager_role.delegate) # all admins have manager role
		self.backend.clear_cache(self.brandon)
		self.assertEqual(self.backend.get_all_permissions(self.brandon),
						 {'test_app.change_author', 'test_app.delete_author'})

		# will approve perms in roles only
		# brandon decides to write on the side; but perms not recognized by roles supervisor
		self.brandon.user_permissions.add(self.change_author)
		self.backend.clear_cache(self.brandon)
		self.assertEqual(self.backend.get_all_permissions(self.brandon),
						 {'test_app.change_author', 'test_app.delete_author'})

		# brandon gets it right this time
		self.brandon.user_permissions.add(self.author_role.delegate)
		self.backend.clear_cache(self.brandon)
		self.assertEqual(self.backend.get_all_permissions(self.brandon),
						 {'test_app.change_author', 'test_app.delete_author',
							 'test_app.add_blog', 'test_app.change_blog'})


@override_settings(
    AUTHENTICATION_BACKENDS=[
		  'django.contrib.auth.backends.ModelBackend',
		  'rolez.backend.RoleModelObjectBackend',
		  'guardian.backends.ObjectPermissionBackend',
		  ],
)
class RoleModelObjectBackendTests(BackendTestsCommon, ModelTestCase):
	def setUp(self):
		super().setUp()
		self.backend = RoleModelObjectBackend()

	def test_user_deny_non_role_obj_perm(self):
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author', self.twain), False)

		# will approve perms in roles only
		assign_perm(self.change_author, self.brandon, self.twain)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author', self.twain), False)

	def test_user_role_obj_perm(self):
		assign_perm(self.manager_role.delegate, self.brandon, self.twain)
		self.backend.clear_cache(self.brandon)

		self.assertIs(self.brandon.has_perm('rolez.use_role_manager', self.twain), True)  # default backend

		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author', self.twain), True)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_author', self.twain), False)

	def test_group_deny_non_role_obj_perm(self):
		self.assertEqual(self.jack.groups.all().__len__(), 1)
		self.assertEqual(self.brandon.groups.all().__len__(), 1)

		# will approve perms in roles only
		assign_perm(self.delete_author, self.admins_group, self.twain)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.delete_author', self.twain), False)

	def test_group_role_obj_perm(self):
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), False)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)

		assign_perm(self.editor_role.delegate, self.users_group, self.twain)

		self.backend.clear_cache(self.jack)
		self.backend.clear_cache(self.brandon)

		self.assertIs(self.jack.has_perm('rolez.use_role_editor', self.twain), True)  # default backend
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog', self.twain), True)
		self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog', self.twain), False) # not author

		self.assertIs(self.brandon.has_perm('rolez.use_role_editor', self.twain), False)
		self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_blog', self.twain), False)
