from django.apps import apps
from django.contrib.auth.models import Permission
from django.conf import settings


def get_role_model():
    return apps.get_model(settings.ROLE_MODEL)


def get_cache_key(obj, perm):
    return (obj._meta.app_label, obj._meta.model_name, obj.pk, perm)


def clear_cache(user):
    # role model backend
    if hasattr(user, '_group_role_model_cache'): del user._group_role_model_cache
    if hasattr(user, '_user_role_model_cache'): del user._user_role_model_cache
    if hasattr(user, '_role_model_cache'): del user._role_model_cache

    # role list model backend
    if hasattr(user, '_role_list_perm_cache'): del user._role_list_perm_cache

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


def get_perm_filter(perm):
    if isinstance(perm, str):
        app_label, codename = perm.split('.', 1)
        return {'content_type__app_label': app_label,
                'codename': codename}
    return {'pk': perm.pk}


def str_to_perm(perm_str):
    return Permission.objects.get(**get_perm_filter(perm_str))


def perms_to_str(perms):
    return {"%s.%s" % (ct, name) for ct, name in
            perms.values_list('content_type__app_label', 'codename')}


def perm_to_str(perm_obj):
    return "%s.%s" % (perm_obj.content_type.app_label, perm_obj.codename)


def get_role_from_delegate(delegate):
    if isinstance(delegate, str):
        delegate = str_to_perm(delegate)
    return delegate.role


def get_perms_from_delegate(delegate):
    return perms_to_str(get_role_from_delegate(delegate).perms)


def get_delegates(perm):
    return perms_to_str(Permission.objects.filter(role__perms=perm))


def get_roles_perms(roles):
    if roles.__len__() > 0 and not isinstance(roles[0], int):
        roles = [role.pk for role in roles]
    return Permission.objects.filter(roles__pk__in=roles)


def test_roles_for_perm(roles, perm):
    return get_roles_perms(roles).filter(**get_perm_filter(perm)).exists()


def test_role_for_perm(role, perm):
    if isinstance(role, int):
        return Permission.objects.filter(roles__pk=role) \
            .filter(**get_perm_filter(perm)) \
            .exists()
    return role.perms \
        .filter(**get_perm_filter(perm)) \
        .exists()
