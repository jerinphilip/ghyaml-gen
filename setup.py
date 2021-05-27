#!/usr/bin/env python

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()


setup(name='ghyamlgen',
      version='0.0',
      description='Generate GitHub YAML for complicated graphs',
      author='Jerin Philip',
      author_email='jerinphilip@live.in',
      url='https://github.com/jerinphilip/ghyaml-gen',
      packages=find_packages(),
      install_requires=required,
)


