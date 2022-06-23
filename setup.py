# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

setup(
    name='conoha',
    version='0.1.20',
    packages=['conoha'],
    description='A command-line interface to the ConoHa.',
    long_description=readme,
    url='https://github.com/giginc/conoha',
    author='Shogo Ishikura',
    author_email='ishikura_shogo@giginc.co.jp',
    license='MIT',
    entry_points={
        'console_scripts': [
            'conoha = conoha.conoha:main'
        ]
    },
    install_requires=['click', 'requests', 'toml']
)
