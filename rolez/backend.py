from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from rolez.models import Role
from rolez.util import get_perm_from_str


def clear_cache(user):
    if hasattr(user, '_role_perm_cache'): del user._role_perm_cache
    if hasattr(user, '_user_role_perm_cache'): del user._user_role_perm_cache
    if hasattr(user, '_group_role_perm_cache'): del user._group_role_perm_cache

    if hasattr(user, '_role_obj_perm_cache'): del user._role_obj_perm_cache

    # and django cache for convenience here
    if hasattr(user, '_group_perm_cache'): del user._group_perm_cache
    if hasattr(user, '_user_perm_cache'): del user._user_perm_cache
    if hasattr(user, '_perm_cache'): del user._perm_cache

    # and guardian cache for convenience here
    if hasattr(user, '_obj_perm_cache'): setattr(user, '_obj_perm_cache', {})


class RoleModelBackend(object):
    def clear_cache(self, user):
        clear_cache(user)

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
        clear_cache(user)

    def authenticate(self, username, password):
        return None

    # the following 3 methods are not implemented since Django currently does not allow
    # addressing other backends. I.e., without a way not responding to itself a call
    # to user.get_*_permissions would cause an infinite loop

    # 	def get_user_permissions(self, user_obj, obj=None):
    # 		pass
    #
    # 	def get_group_permissions(self, user_obj, obj=None):
    # 		pass
    #
    # 	def get_all_permissions(self, user_obj, obj=None):
    # 		pass

    def has_perm(self, user_obj, perm, obj=None):
        if obj is None:
            return False

        if not hasattr(user_obj, '_role_obj_perm_cache'):
            user_obj._role_obj_perm_cache = {}

        key = self.get_cache_key(obj, perm)
        if key not in user_obj._role_obj_perm_cache:
            user_obj._role_obj_perm_cache[key] = False
            perm = get_perm_from_str(perm)
            if not hasattr(perm, 'role'):
                # check regular perms; i.e. exclude delegates, not to get in a infinite loop
                # if could django allowed choosing backends, would also be possible
                # to include roles in roles (delegates in role permissions)
                delegates = Permission.objects.filter(role__perms=perm) \
                    .values_list('content_type__app_label', 'codename').order_by()
                delegates = {"%s.%s" % (ct, name) for ct, name in delegates}
                for delegate in delegates:
                    if user_obj.has_perm(delegate, obj):  # ??!
                        user_obj._role_obj_perm_cache[key] = True
        return user_obj._role_obj_perm_cache[key]

    def get_cache_key(self, obj, perm):
        return (obj._meta.app_label, obj._meta.model_name, obj.pk, perm)

# 	def has_module_perms(self, user_obj, app_label):
# 		pass
