import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = 'fake-key'

INSTALLED_APPS = (
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.admin',
	'rolez',
	'tests.test_app',
	)

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'rolez.backend.RoleModelBackend',
)

# ROOT_URLCONF = 'rolez.urls'
