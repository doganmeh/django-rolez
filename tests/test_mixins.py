from rolez.mixins import _has_backend

from django.contrib.auth.models import Permission, Group
from django.test import TestCase as ModelTestCase, override_settings

from rolez.util import clear_cache
from tests.test_app.models import Author, Blog
from rolez.models import Role
from rolez.backend import RoleModelBackend, RoleObjectBackend
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from guardian.shortcuts import assign_perm

UserModel = get_user_model()


class HasBackendTests(ModelTestCase):
    @override_settings(
        AUTHENTICATION_BACKENDS=[
            'django.contrib.auth.backends.ModelBackend',
            'rolez.backend.RoleModelBackend',
            'rolez.backend.RoleObjectBackend',
            'guardian.backends.ObjectPermissionBackend',
        ],
    )
    def test_has_backend_inclusive(self):
        self.assertIs(_has_backend('ModelBackend'), True)
        self.assertIs(_has_backend('RoleModelBackend'), True)
        self.assertIs(_has_backend('RoleObjectBackend'), True)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
        ],
    )
    def test_has_backend_exclusive(self):
        self.assertIs(_has_backend('ModelBackend'), False)
        self.assertIs(_has_backend('RoleModelBackend'), False)
        self.assertIs(_has_backend('RoleObjectBackend'), False)


class UserRoleMixinTestsCommon(object):
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
        self.change_author = Permission.objects.get(
            content_type=content_type, codename='change_author')
        self.delete_author = Permission.objects.get(
            content_type=content_type, codename='delete_author')

        content_type = ContentType.objects.get_for_model(Blog)
        self.change_blog = Permission.objects.get(content_type=content_type, codename='change_blog')
        self.add_blog = Permission.objects.get(content_type=content_type, codename='add_blog')

        self.manager_role.perms.add(self.change_author, self.delete_author)
        self.editor_role.perms.add(self.change_blog)
        self.author_role.perms.add(self.change_blog, self.add_blog)

        self.twain = Author.objects.create(name="twain")
        self.twain_blog = Blog.objects.create(name="twain personal blog")

        self.all_perms = {
            'rolez.add_role',
            'rolez.change_role',
            'rolez.delete_role',
            'rolez.use_role_author',
            'rolez.use_role_editor',
            'rolez.use_role_manager',
            'test_app.add_author',
            'test_app.add_blog',
            'test_app.add_entry',
            'test_app.add_roleuser',
            'test_app.change_author',
            'test_app.change_blog',
            'test_app.change_entry',
            'test_app.change_roleuser',
            'test_app.delete_author',
            'test_app.delete_blog',
            'test_app.delete_entry',
            'test_app.delete_roleuser',
        }

    def test_super_user_model_perms(self):
        self.brandon.is_superuser = True
        for perm in self.all_perms:
            self.assertIn(perm, self.brandon.get_all_permissions())
            self.assertIn(perm, self.brandon.get_group_role_perms())
            self.assertIn(perm, self.brandon.get_all_role_perms())


@override_settings(
    AUTHENTICATION_BACKENDS=[
        'django.contrib.auth.backends.ModelBackend',
    ],
)
class UserRoleMixinDefaultBackendTests(UserRoleMixinTestsCommon, ModelTestCase):
    def setUp(self):
        super().setUp()

    def test_user_allow_role_model_perm(self):
        self.brandon.user_permissions.add(self.manager_role.delegate)
        self.assertIs(self.brandon.has_role_perm('rolez.use_role_manager'), True)  # default backend

        clear_cache(self.brandon)
        self.assertIs(self.brandon.has_role_perm('test_app.change_author'), True)
        self.assertIs(self.jack.has_role_perm('test_app.change_author'), False)

    def test_group_allow_role_model_perm(self):
        self.assertIs(self.jack.has_role_perm('test_app.change_blog'), False)
        self.assertIs(self.jack.has_role_perm('test_app.add_blog'), False)

        self.users_group.permissions.add(self.editor_role.delegate)  # all users have editor role

        clear_cache(self.jack)
        clear_cache(self.brandon)

        self.assertIs(self.jack.has_role_perm('rolez.use_role_editor'), True)  # default backend
        self.assertIs(self.jack.has_role_perm('test_app.change_blog'), True)
        self.assertIs(self.jack.has_role_perm('test_app.add_blog'), False)  # not author

        self.assertIs(self.brandon.has_role_perm('rolez.use_role_editor'), False)
        self.assertIs(self.brandon.has_role_perm('test_app.change_blog'), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.brandon.get_all_permissions(), set())

        self.admins_group.permissions.add(
            self.manager_role.delegate)  # all admins have manager role
        clear_cache(self.brandon)
        self.assertEqual(self.brandon.get_all_permissions(),
                         {'rolez.use_role_manager'})

        self.assertEqual(self.brandon.get_all_role_perms(),
                         {'rolez.use_role_manager', 'test_app.change_author',
                          'test_app.delete_author'})

        # will approve perms in roles only
        # brandon decides to write on the side; and perms recognized by roles supervisor
        self.brandon.user_permissions.add(self.add_blog)
        clear_cache(self.brandon)
        self.assertEqual(self.brandon.get_all_permissions(),
                         {'rolez.use_role_manager', 'test_app.add_blog'})

        # brandon wants the entire role
        self.brandon.user_permissions.add(self.author_role.delegate)
        clear_cache(self.brandon)
        self.assertEqual(self.brandon.get_all_role_perms(),
                         {'rolez.use_role_manager', 'rolez.use_role_author',
                          'test_app.change_author', 'test_app.delete_author',
                          'test_app.add_blog', 'test_app.change_blog'})


@override_settings(
    AUTHENTICATION_BACKENDS=[
        'django.contrib.auth.backends.ModelBackend',
        'rolez.backend.RoleModelBackend',
    ],
)
class UserRoleMixinModelTests(UserRoleMixinTestsCommon, ModelTestCase):
    def setUp(self):
        super().setUp()

    def test_user_allow_role_model_perm(self):
        self.brandon.user_permissions.add(self.manager_role.delegate)
        self.assertIs(self.brandon.has_role_perm('rolez.use_role_manager'), True)  # default backend

        clear_cache(self.brandon)
        self.assertIs(self.brandon.has_role_perm('test_app.change_author'), True)
        self.assertIs(self.jack.has_role_perm('test_app.change_author'), False)

    def test_group_allow_role_model_perm(self):
        self.assertIs(self.jack.has_role_perm('test_app.change_blog'), False)
        self.assertIs(self.jack.has_role_perm('test_app.add_blog'), False)

        self.users_group.permissions.add(self.editor_role.delegate)  # all users have editor role

        clear_cache(self.jack)
        clear_cache(self.brandon)

        self.assertIs(self.jack.has_role_perm('rolez.use_role_editor'), True)  # default backend
        self.assertIs(self.jack.has_role_perm('test_app.change_blog'), True)
        self.assertIs(self.jack.has_role_perm('test_app.add_blog'), False)  # not author

        self.assertIs(self.brandon.has_role_perm('rolez.use_role_editor'), False)
        self.assertIs(self.brandon.has_role_perm('test_app.change_blog'), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.brandon.get_all_permissions(), set())

        self.admins_group.permissions.add(
            self.manager_role.delegate)  # all admins have manager role
        clear_cache(self.brandon)
        self.assertEqual(self.brandon.get_all_permissions(),
                         {'rolez.use_role_manager', 'test_app.change_author',
                          'test_app.delete_author'})

        self.assertEqual(self.brandon.get_all_role_perms(),
                         {'rolez.use_role_manager', 'test_app.change_author',
                          'test_app.delete_author'})

        # will approve perms in roles only
        # brandon decides to write on the side; and perms recognized by roles supervisor
        self.brandon.user_permissions.add(self.add_blog)
        clear_cache(self.brandon)
        self.assertEqual(self.brandon.get_all_permissions(),
                         {'rolez.use_role_manager', 'test_app.change_author',
                          'test_app.delete_author', 'test_app.add_blog'})

        # brandon wants the entire role
        self.brandon.user_permissions.add(self.author_role.delegate)
        clear_cache(self.brandon)
        self.assertEqual(self.brandon.get_all_permissions(),
                         {'rolez.use_role_manager', 'rolez.use_role_author',
                          'test_app.change_author', 'test_app.delete_author',
                          'test_app.add_blog', 'test_app.change_blog'})


@override_settings(
    AUTHENTICATION_BACKENDS=[
        'django.contrib.auth.backends.ModelBackend',
        'rolez.backend.RoleObjectBackend',
        'guardian.backends.ObjectPermissionBackend',
    ],
)
class UserRoleMixinObjectTests(UserRoleMixinTestsCommon, ModelTestCase):
    def setUp(self):
        super().setUp()


    def test_user_allow_non_role_obj_perm(self):
        self.assertIs(self.brandon.has_role_perm('test_app.change_author', self.twain), False)
        assign_perm(self.change_author, self.brandon, self.twain)
        clear_cache(self.brandon)
        self.assertIs(self.brandon.has_role_perm('test_app.change_author', self.twain), True)

    def test_user_allow_role_obj_perm(self):
        assign_perm(self.manager_role.delegate, self.brandon, self.twain)
        clear_cache(self.brandon)

        self.assertIs(self.brandon.has_perm('rolez.use_role_manager', self.twain), True)  # default backend

        self.assertIs(self.brandon.has_role_perm('test_app.change_author', self.twain), True)
        self.assertIs(self.jack.has_role_perm('test_app.change_author', self.twain), False)


    def test_group_deny_non_role_obj_perm(self):
        self.assertEqual(self.jack.groups.all().__len__(), 1)
        self.assertEqual(self.brandon.groups.all().__len__(), 1)

        assign_perm(self.delete_author, self.admins_group, self.twain)
        self.assertIs(self.brandon.has_role_perm('test_app.delete_author', self.twain), True)


    def test_group_allow_role_obj_perm(self):
        self.assertIs(self.jack.has_role_perm('test_app.change_blog'), False)
        self.assertIs(self.jack.has_role_perm('test_app.add_blog'), False)

        assign_perm(self.editor_role.delegate, self.users_group, self.twain)

        clear_cache(self.jack)
        clear_cache(self.brandon)

        self.assertIs(self.jack.has_perm('rolez.use_role_editor', self.twain), True)  # default backend
        self.assertIs(self.jack.has_role_perm('test_app.change_blog', self.twain), True)
        self.assertIs(self.jack.has_role_perm('test_app.add_blog', self.twain), False)  # not author

        self.assertIs(self.brandon.has_perm('rolez.use_role_editor', self.twain), False)
        self.assertIs(self.brandon.has_role_perm('test_app.change_blog', self.twain), False)
