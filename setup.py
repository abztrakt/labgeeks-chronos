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
        'setuptools',
        'labgeeks-people',
        'South==0.7.3',
    ],
)
