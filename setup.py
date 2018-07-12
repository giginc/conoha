# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

setup(
    name='conoha',
    version='0.1.1',
    packages=['conoha'],
    description='A command-line interface to the ConoHa.',
    long_description=readme,
    url='https://github.com/issy-s16/conoha',
    author='Shogo Ishikura',
    author_email='ishikura.shogo@gmail.com',
    license='MIT',
    entry_points={
        'console_scripts': [
            'conoha = conoha.conoha:main'
        ]
    },
    install_requires=['click', 'requests', 'toml']
)
