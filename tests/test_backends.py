from django.contrib.auth.models import Permission, Group
from django.test import TestCase as ModelTestCase, override_settings
from tests.test_app.models import Author, Blog, Role
from rolez.backend import RoleModelBackend, RoleObjectBackend
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from guardian.shortcuts import assign_perm

UserModel = get_user_model()

class BackendTestsCommon(object):
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

        author_ct = ContentType.objects.get_for_model(Author)
        self.change_author = Permission.objects.get(content_type=author_ct, codename='change_author')
        self.delete_author = Permission.objects.get(content_type=author_ct, codename='delete_author')

        blog_ct = ContentType.objects.get_for_model(Blog)
        self.change_blog = Permission.objects.get(content_type=blog_ct, codename='change_blog')
        self.add_blog = Permission.objects.get(content_type=blog_ct, codename='add_blog')

        self.manager_role.perms.add(self.change_author, self.delete_author)
        self.editor_role.perms.add(self.change_blog)
        self.author_role.perms.add(self.change_blog, self.add_blog)

        self.twain = Author.objects.create(name="twain")
        self.twain_blog = Blog.objects.create(name="twain personal blog")

    def test_user_deny_non_role_model_perm(self):
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author'), False)

        # will approve perms in roles only
        self.brandon.user_permissions.add(self.change_author)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author'), False)

    def test_group_deny_non_role_model_perm(self):
        self.assertEqual(self.jack.groups.all().__len__(), 1)
        self.assertEqual(self.brandon.groups.all().__len__(), 1)

        # will approve perms in roles only
        self.admins_group.permissions.add(self.delete_author)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.delete_author'), False)


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

    def test_user_allow_role_model_perm(self):
        self.brandon.user_permissions.add(self.manager_role.delegate)
        self.assertIs(self.brandon.has_perm('test_app.use_role_manager'), True)  # default backend

        self.backend.clear_cache(self.brandon)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author'), True)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_author'), False)

    def test_group_allow_role_model_perm(self):
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), False)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)

        self.users_group.permissions.add(self.editor_role.delegate)  # all users have editor role

        self.backend.clear_cache(self.jack)
        self.backend.clear_cache(self.brandon)

        self.assertIs(self.jack.has_perm('test_app.use_role_editor'), True)  # default backend
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), True)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)  # not author

        self.assertIs(self.brandon.has_perm('test_app.use_role_editor'), False)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_blog'), False)

    def test_get_all_permissions(self):
        self.assertEqual(self.backend.get_all_permissions(self.brandon), set())

        self.admins_group.permissions.add(self.manager_role.delegate)  # all admins have manager role
        self.backend.clear_cache(self.brandon)
        self.assertEqual(self.backend.get_all_permissions(self.brandon),
                         {'test_app.change_author', 'test_app.delete_author'})

        # will approve perms in roles only
        # brandon decides to write on the side; but perms not recognized by roles supervisor
        self.brandon.user_permissions.add(self.add_blog)
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
        'rolez.backend.RoleObjectBackend',
        'guardian.backends.ObjectPermissionBackend',
    ],
)
class RoleObjectBackendTests(BackendTestsCommon, ModelTestCase):
    def setUp(self):
        super().setUp()
        self.backend = RoleObjectBackend()

    def test_user_deny_role_model_perm(self):
        self.brandon.user_permissions.add(self.manager_role.delegate)
        self.assertIs(self.brandon.has_perm('test_app.use_role_manager'), True)  # default backend

        self.backend.clear_cache(self.brandon)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author'), False)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_author'), False)

    def test_group_deny_role_model_perm(self):
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), False)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)

        self.users_group.permissions.add(self.editor_role.delegate)  # all users have editor role

        self.backend.clear_cache(self.jack)
        self.backend.clear_cache(self.brandon)

        self.assertIs(self.jack.has_perm('test_app.use_role_editor'), True)  # default backend
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), False)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)  # not author

        self.assertIs(self.brandon.has_perm('test_app.use_role_editor'), False)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_blog'), False)

    def test_user_deny_non_role_obj_perm(self):
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author', self.twain), False)

        # will approve perms in roles only
        assign_perm(self.change_author, self.brandon, self.twain)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author', self.twain), False)

    def test_user_allow_role_obj_perm(self):
        assign_perm(self.manager_role.delegate, self.brandon, self.twain)
        self.backend.clear_cache(self.brandon)

        self.assertIs(self.brandon.has_perm('test_app.use_role_manager', self.twain), True)  # default backend

        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_author', self.twain), True)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_author', self.twain), False)

    def test_group_deny_non_role_obj_perm(self):
        self.assertEqual(self.jack.groups.all().__len__(), 1)
        self.assertEqual(self.brandon.groups.all().__len__(), 1)

        # will approve perms in roles only
        assign_perm(self.delete_author, self.admins_group, self.twain)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.delete_author', self.twain), False)

    def test_group_allow_role_obj_perm(self):
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog'), False)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog'), False)

        assign_perm(self.editor_role.delegate, self.users_group, self.twain)

        self.backend.clear_cache(self.jack)
        self.backend.clear_cache(self.brandon)

        self.assertIs(self.jack.has_perm('test_app.use_role_editor', self.twain), True)  # default backend
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.change_blog', self.twain), True)
        self.assertIs(self.backend.has_perm(self.jack, 'test_app.add_blog', self.twain), False)  # not author

        self.assertIs(self.brandon.has_perm('test_app.use_role_editor', self.twain), False)
        self.assertIs(self.backend.has_perm(self.brandon, 'test_app.change_blog', self.twain), False)
