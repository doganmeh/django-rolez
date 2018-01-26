from django.contrib.auth.models import Permission


def get_perm_from_str(str):
	app_label, codename = str.split('.', 1)
	return Permission.objects.get(content_type__app_label=app_label,
								  codename=codename)
