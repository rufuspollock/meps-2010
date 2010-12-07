from setuptools import setup, find_packages
__version__ = '0.1'
long_description = 'MEPs'

setup(
    name = 'meps',
    version = __version__,
    py_modules=['meps'],
    install_requires=[
        'BeautifulSoup'
        ],
    # package_dir = {'meps': ''},
    # packages = find_packages(),

    # metadata
    author = 'Rufus Pollock (Open Knowledge Foundation)',
    url = 'http://bitbucket.org/rgrp/meps',
    author_email = 'rufus.pollock@okfn.org',
    description = long_description.split()[0],
    long_description = long_description,
    license = 'MIT',
    keywords = 'meps datapkg',
    download_url = '',
    zip_safe=False,
)

