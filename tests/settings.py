DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

MIDDLEWARE_CLASSES = (
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
)

INSTALLED_APPS = ("multi_import", "tests",)

SITE_ID = 1

SECRET_KEY = "foobar"  # noqa
