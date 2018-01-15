from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.test import TestCase as ModelTestCase  # use when querying models
from unittest import TestCase as NonModelTestCase  # use otherwise
from tests.test_app.models import Author
from rolez.models import Role
from django.contrib.contenttypes.models import ContentType

# assert list: https://docs.python.org/3/library/unittest.html#assert-methods:

# Method						Checks that
# assertEqual(a, b)				a == b
# assertNotEqual(a, b)			a != b
# assertTrue(x)					bool(x) is True
# assertFalse(x)				bool(x) is False
# assertIs(a, b)				a is b
# assertIsNot(a, b)				a is not b
# assertIsNone(x)				x is None
# assertIsNotNone(x)			x is not None
# assertIn(a, b)				a in b
# assertNotIn(a, b)				a not in b
# assertIsInstance(a, b)		isinstance(a, b)
# assertNotIsInstance(a, b)		not isinstance(a, b)

# django specific: https://docs.djangoproject.com/en/dev/topics/testing/tools/#assertions

# testing views: https://docs.djangoproject.com/en/dev/intro/tutorial05/#the-django-test-client


class RoleTests(ModelTestCase):
	def setUp(self):
		john = Author.objects.create(name="John")

	def test_create_delete_role(self):
		role = Role(name="Admin")
		role.save()
		self.assertIsNotNone(role.delegate)

		ctype = ContentType.objects.get_for_model(role)  # takes obj or model
		delegate = Permission.objects.filter(content_type=ctype, codename=role.code_name())
		self.assertEqual(list(delegate).__len__(), 1)  # delegate created

		role.delete()
		delegate = Permission.objects.filter(content_type=ctype, codename=role.code_name())
		self.assertEqual(list(delegate).__len__(), 0)  # delegate also deleted

	def test_create_duplicate_role(self):
		role = Role(name="Admin")
		role.save()
		role = Role(name="Admin")
		with self.assertRaises(IntegrityError):
			role.save()
