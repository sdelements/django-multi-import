#!/usr/bin/env python
import os
import sys


if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'


import django                             # flake8: noqa
from django.conf import settings          # flake8: noqa
from django.test.utils import get_runner  # flake8: noqa

if __name__ == "__main__":
    if hasattr(django, 'setup'):
        django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True, failfast=False)
    failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))
