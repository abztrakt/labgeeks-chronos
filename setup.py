from setuptools import setup

setup(
    name = 'labgeeks-chronos',
    version = '1.0',
    license = 'Apache',
    url = 'http://github.com/abztrakt/labgeeks_chronos',
    description = 'The punchclock/timekeeping app for the labgeeks staff management tool.',
    author = 'Craig Stimmel',
    packages = ['labgeeks_chronos',],
    install_requires = [
        'django==1.4',
        'mock==1.0.1',
        'requests',
        'setuptools',
        'labgeeks-people',
        'south',
        'django-compressor==1.1.2',
    ],
)
