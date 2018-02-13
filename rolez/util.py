from django.contrib.auth.models import Permission


def get_cache_key(obj, perm):
    return (obj._meta.app_label, obj._meta.model_name, obj.pk, perm)


def clear_cache(user):
    # role model backend
    if hasattr(user, '_group_role_model_cache'): del user._group_role_model_cache
    if hasattr(user, '_user_role_model_cache'): del user._user_role_model_cache
    if hasattr(user, '_role_model_cache'): del user._role_model_cache

    # role object backend
    if hasattr(user, '_role_obj_cache'): del user._role_obj_cache

    # role mixin
    if hasattr(user, '_group_role_perm_cache'): del user._group_role_perm_cache
    if hasattr(user, '_user_role_perm_cache'): del user._user_role_perm_cache
    if hasattr(user, '_all_role_perm_cache'): del user._all_role_perm_cache

    # and django cache for convenience here
    if hasattr(user, '_group_perm_cache'): del user._group_perm_cache
    if hasattr(user, '_user_perm_cache'): del user._user_perm_cache
    if hasattr(user, '_perm_cache'): del user._perm_cache

    # and guardian cache for convenience here
    if hasattr(user, '_obj_perm_cache'): setattr(user, '_obj_perm_cache', {})


def str_to_perm(str):
    app_label, codename = str.split('.', 1)
    return Permission.objects.get(content_type__app_label=app_label,
                                  codename=codename)


def get_role_from_delegate(delegate):
    if isinstance(delegate, str):
        delegate = str_to_perm(delegate)
    return delegate.role


def perms_to_str(perms):
    return {"%s.%s" % (ct, name) for ct, name in
            perms.values_list('content_type__app_label', 'codename')}


def get_perms_from_delegate(delegate):
    return perms_to_str(get_role_from_delegate(delegate).perms)


def get_delegates(perm):
    return perms_to_str(Permission.objects.filter(role__perms=perm))