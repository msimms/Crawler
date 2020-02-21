from setuptools import setup, find_packages

requirements = ['requests', 'beautifulsoup4', 'url-normalize']

setup(
    name='crawler',
    version='1.0.0',
    description='',
    url='https://github.com/msimms/Crawler',
    author='Mike Simms',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=requirements,
)

