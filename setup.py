import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'pyramid_zodbconn',
    'transaction',
    'pyramid_tm',
    'ZODB3',
    'waitress',
    'WebTest',
    'WTForms',
    'WebHelpers',
    ]

setup(name='djoser',
      version='0.0',
      description='djoser',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='david moore',
      author_email='info@linuxsoftware.co.nz',
      url='http://linuxsoftware.co.nz',
      keywords='web pyramid djoser',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="djoser",
      entry_points="""\
      [paste.app_factory]
      main = djoser:main
      """,
      )
