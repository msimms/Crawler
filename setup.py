from setuptools import setup, find_packages

requirements = ['requests', 'beautifulsoup4']

setup(
    name='webcrawler',
    version='1.0.0',
    description='',
    url='https://github.com/msimms/Crawler',
    author='Mike Simms',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=requirements,
)

