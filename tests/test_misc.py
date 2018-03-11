from django.contrib.auth.models import Permission, Group
from django.db import IntegrityError
from django.test import TestCase as ModelTestCase, override_settings  # use when querying models
from unittest import TestCase as NonModelTestCase  # use otherwise
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from rolez.util import test_roles_for_perm, test_role_for_perm, get_role_model
from tests.test_app.models import Author, Blog

UserModel = get_user_model()
Role = get_role_model()


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
        role = Role.objects.create(name="Maintenance")
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


class UtilityTests(ModelTestCase):
    def setUp(self):
        self.admins_group = Group.objects.create(name='admins')
        self.users_group = Group.objects.create(name='users')

        self.brandon = UserModel.objects.create(username='brandon')
        self.jack = UserModel.objects.create(username='jack')

        self.brandon.groups.add(self.admins_group)
        self.jack.groups.add(self.users_group)

        self.manager_role = Role.objects.create(name='manager')  # author add, change, delete
        self.editor_role = Role.objects.create(name='editor')  # blog change
        self.author_role = Role.objects.create(name='author')  # blog change, add

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

    def test_test_roles_for_perm(self):
        self.assertIs(test_roles_for_perm([self.manager_role, self.editor_role], self.change_blog), True)
        self.assertIs(test_roles_for_perm([self.manager_role], self.change_author), True)
        self.assertIs(test_roles_for_perm([self.manager_role], self.add_blog), False)

        self.assertIs(test_roles_for_perm([self.manager_role.pk], self.change_author), True)
        self.assertIs(test_roles_for_perm([self.manager_role.pk], self.add_blog), False)

        self.assertIs(test_roles_for_perm([self.manager_role.pk], 'test_app.change_author'), True)
        self.assertIs(test_roles_for_perm([self.manager_role.pk], 'test_app.add_blog'), False)

    def test_test_role_for_perm(self):
        self.assertIs(test_role_for_perm(self.manager_role, self.change_author), True)
        self.assertIs(test_role_for_perm(self.manager_role, self.add_blog), False)

        self.assertIs(test_role_for_perm(self.manager_role.pk, self.change_author), True)
        self.assertIs(test_role_for_perm(self.manager_role.pk, self.add_blog), False)

        self.assertIs(test_role_for_perm(self.manager_role.pk, 'test_app.change_author'), True)
        self.assertIs(test_role_for_perm(self.manager_role.pk, 'test_app.add_blog'), False)

