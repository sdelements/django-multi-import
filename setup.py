import os
from setuptools import setup, find_packages


def read_file(filename):
    """Read a file into a string"""
    path = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(path, filename)
    try:
        return open(filepath).read()
    except IOError:
        return ''

install_requires = [
    'chardet',
    'tablib',
    'six',
]


setup(
    name='django-multi_import',
    version='1.0.4',
    author='Simon Bartlett',
    author_email='simon@securitycompass.com',
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/sdelements/django-multi-importer',
    license='MIT',
    description='Import/export multi Django resources together atomically',
    classifiers=[
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django',
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
    ],
    long_description=read_file('README.rst'),
    test_suite="runtests.runtests",
    zip_safe=False,
    requires=['django (>=1.11)', 'djangorestframework (>=3.0)'],
    install_requires=install_requires
)
