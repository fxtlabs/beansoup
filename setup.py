from os import path
import re
from setuptools import setup
import sys

# Check if the version is sufficient.
if sys.version_info[:2] < (3,3):
    raise SystemExit("ERROR: Insufficient Python version; you need v3.3 or higher.")

here = path.abspath(path.dirname(__file__))

# Get the version string without importing the package
with open(path.join(here, 'beansoup', 'version.py'), 'rt') as f:
    version = re.search(r"__version__ = '(.*?)'", f.read()).group(1)
    
with open(path.join(here, 'README.rst'), 'rt', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='beansoup',

    version=version,

    description='A companion to beancount, a command-line double-entry accounting tool',
    long_description=long_description,

    # Project homepage
    url='https://github.com/fxtlabs/beansoup',

    # Author details
    author='Filippo Tampieri',
    author_email='fxt@fxtlabs.com',

    license='GPLv2',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',

        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Topic :: Office/Business :: Financial',
        'Topic :: Office/Business :: Financial :: Accounting',
        'Topic :: Office/Business :: Financial :: Investment',
    
        # Use the same license as beancount
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',

        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Operating System :: OS Independent',
    ],

    keywords=['accounting', 'investing'],

    packages=['beansoup'],

    install_requires=['beancount'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov', 'coverage', 'python-dateutil'],
)
