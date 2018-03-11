from django.conf import settings
from django.contrib.auth.models import Permission

from rolez.util import clear_cache, get_cache_key, str_to_perm, get_perms_from_delegate, \
    perms_to_str, get_delegates


def _has_backend(name):
    for backend in settings.AUTHENTICATION_BACKENDS:
        if backend.endswith(name):
            return True
    return False


class UserRoleMixin(object):
    def clear_cache(self):
        clear_cache(self)

    def _get_role_perms(self, obj, from_name):
        super_ = getattr(super(), 'get_%s_permissions' % from_name)
        if (obj is None and _has_backend('RoleModelBackend')
                or obj is not None and _has_backend('RoleObjectBackend')):
            return super_(obj)

        cache_name = '_%s_role_perm_cache' % from_name
        if hasattr(self, cache_name):
            return getattr(self, cache_name)

        if self.is_superuser:
            perms_role_added = perms_to_str(Permission.objects.all())
        else:
            perms = super_(obj)
            perms_role_added = set(perms)
            app_name, _ = settings.ROLE_MODEL.split('.')
            for perm in perms:
                if perm[:perm.index('.')] == app_name:
                    perm = str_to_perm(perm)
                    if hasattr(perm, 'role'):
                        perms_role_added.update(get_perms_from_delegate(perm))
                    # todo: this will make n trips to the db
        setattr(self, cache_name, perms_role_added)
        return perms_role_added

    def get_group_role_perms(self, obj=None):
        return self._get_role_perms(obj, 'group')

    def get_all_role_perms(self, obj=None):
        return self._get_role_perms(obj, 'all')

    def has_role_perm(self, perm, obj=None):
        if super().has_perm(perm, obj):
            # like django, this can only refer to its super, not get_(group|all)_permissions
            # directly bc a backend is not required to implement them all
            return True

        if obj is None and not _has_backend('RoleModelBackend'):
            return perm in self.get_all_role_perms()

        if obj is not None and not _has_backend('RoleObjectBackend'):
            if not hasattr(self, '_role_obj_cache'):
                self._role_obj_cache = {}

            key = get_cache_key(obj, perm)
            if key in self._role_obj_cache:
                return self._role_obj_cache[key]

            # this should be more performant than RoleObjectBackend since it runs when super fails
            # in the other, they both always run
            self._role_obj_cache[key] = False
            perm = str_to_perm(perm)
            if not hasattr(perm, 'role'):  # not delegate
                for delegate in get_delegates(perm):
                    if super().has_perm(delegate, obj):
                        self._role_obj_cache[key] = True
                        return True
        return False

# 	def has_module_perms(self, user_obj, app_label):
# 		pass
