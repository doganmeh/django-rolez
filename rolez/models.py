import re
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models

UserModel = get_user_model()


class Role(models.Model):
	name = models.CharField(
		max_length=90, unique=True,  # auth.Permission codename length is 100
		error_messages={
			'unique': "That name is taken, sorry!. Try another one.",
			},
		)
	delegate = models.OneToOneField(Permission, on_delete=models.CASCADE,
									related_name='delegate_of')
	perms = models.ManyToManyField(Permission, related_name='in_roles')

	def codename(self):
		return 'use_role_' + re.sub(r'([^\s\w]|_)+', '', self.name).replace(' ', '_')

	def save(self, **kwargs):
		if not hasattr(self, 'delegate'):
			ctype = ContentType.objects.get_for_model (self) # takes obj or model
			self.delegate = Permission.objects.create(
				content_type = ctype,
				codename = self.codename(),
				)
			super().save(**kwargs)

	def delete(self, **kwargs):
		super().delete(**kwargs)
		self.delegate.delete()
