from django.contrib.auth.models import Permission, Group
from django.db import IntegrityError
from django.test import TestCase as ModelTestCase, override_settings  # use when querying models
from unittest import TestCase as NonModelTestCase  # use otherwise
from rolez.models import Role
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from rolez.mixins import _has_backend

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

