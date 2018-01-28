from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from rolez.models import Role
from rolez.util import get_perm_from_str


class RoleModelBackend(object):
	def clear_cache(self, user):
		if hasattr(user, '_role_perm_cache'): del user._role_perm_cache
		if hasattr(user, '_user_role_perm_cache'): del user._user_role_perm_cache
		if hasattr(user, '_group_role_perm_cache'): del user._group_role_perm_cache

		# and django cache for convenience here
		if hasattr(user, '_group_perm_cache'): del user._group_perm_cache
		if hasattr(user, '_user_perm_cache'): del user._user_perm_cache
		if hasattr(user, '_perm_cache'): del user._perm_cache

		# and guardian cache for convenience here
		if hasattr(user, '_obj_perm_cache'): del user._obj_perm_cache


	def authenticate(self, username, password):
		return None

	def _get_user_permissions(self, user_obj):
		return Permission.objects.filter(roles__delegate__in=user_obj.user_permissions.all())

	def _get_group_permissions(self, user_obj):
		user_groups_field = get_user_model()._meta.get_field('groups')
		group_perms = Permission.objects.filter(
			**{'group__' + user_groups_field.related_query_name(): user_obj})
		return Permission.objects.filter(roles__delegate__in=group_perms)

	def _get_permissions(self, user_obj, obj, from_name):
		if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
			return set()
		perm_cache_name = '_%s_role_perm_cache' % from_name
		if not hasattr(user_obj, perm_cache_name):
			perms = getattr(self, '_get_%s_permissions' % from_name)(user_obj)
			perms = perms.values_list('content_type__app_label', 'codename').order_by()
			setattr(user_obj, perm_cache_name, {"%s.%s" % (ct, name) for ct, name in perms})
		return getattr(user_obj, perm_cache_name)

	def get_user_permissions(self, user_obj, obj=None):
		return self._get_permissions(user_obj, obj, 'user')

	def get_group_permissions(self, user_obj, obj=None):
		return self._get_permissions(user_obj, obj, 'group')

	def get_all_permissions(self, user_obj, obj=None):
		if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
			return set()
		if not hasattr(user_obj, '_role_perm_cache'):
			user_obj._role_perm_cache = set()
			user_obj._role_perm_cache.update(self.get_user_permissions(user_obj))
			user_obj._role_perm_cache.update(self.get_group_permissions(user_obj))
		return user_obj._role_perm_cache

	def has_perm(self, user_obj, perm, obj=None):
		if not user_obj.is_active:
			return False
		return perm in self.get_all_permissions(user_obj, obj)

	def has_module_perms(self, user_obj, app_label):
		"""
		Return True if user_obj has any roles with permissions in the given app_label.
		"""
		if not user_obj.is_active:
			return False
		for perm in self.get_all_permissions(user_obj):
			if perm[:perm.index('.')] == app_label:
				return True
		return False


class RoleModelObjectBackend(object):
	def clear_cache(self, user):
		# and django cache for convenience here
		if hasattr(user, '_group_perm_cache'): del user._group_perm_cache
		if hasattr(user, '_user_perm_cache'): del user._user_perm_cache
		if hasattr(user, '_perm_cache'): del user._perm_cache

	def authenticate(self, username, password):
		return None

# 	def get_user_permissions(self, user_obj, obj=None):
# 		pass
#
# 	def get_group_permissions(self, user_obj, obj=None):
# 		pass
#
# 	def get_all_permissions(self, user_obj, obj=None):
# 		pass

	def has_perm(self, user_obj, perm, obj=None):
		perm = get_perm_from_str(perm)
		if hasattr(perm, 'role'):
			return False # exclude delegates not to get in a infinite loop
		# if could choose backends, would also be able to include roles in roles (
		# delegates in role permissions)

		delegates = Permission.objects.filter(role__perms=perm) \
			.values_list('content_type__app_label', 'codename').order_by()
		delegates = {"%s.%s" % (ct, name) for ct, name in delegates}
		for delegate in delegates:
			if user_obj.has_perm(delegate, obj): 										# ??!
				return True
		return False

# 	def has_module_perms(self, user_obj, app_label):
# 		pass
