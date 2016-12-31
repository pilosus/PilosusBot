from os.path import join, dirname

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '0.1.0'

# read common PyPI packages needed for this module
with open("requirements/common.txt") as packages_file:
    packages = packages_file.read().splitlines()
requirements = list(filter(lambda x: "http" not in x, packages))

# read PyPI packages needed for testing
with open("requirements/testing.txt") as test_packages_file:
    test_packages = test_packages_file.read().splitlines()
test_requirements = list(filter(lambda x: "http" not in x, test_packages))

# long description
with open('README.rst') as readme_file:
    readme = readme_file.read()


setup(
    name='PilosusBot',
    packages=['PilosusBot'],
    version=version,
    author='Vitaly R. Samigullin',
    author_email='vrs@pilosus.org',
    description='A Flask application for running Telegram Bot featuring natural language processing',
    long_description=readme,
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        'Natural Language :: Russian',
        'Natural Language :: English',
        'Topic :: Communications :: Chat',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
    ],
    test_suite='tests',
    tests_require=test_requirements,
)
