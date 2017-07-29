import subprocess

import yaml
from setuptools import setup, find_packages
from conda_shell import __version__


install_requires = []
with open('environment.yml') as env_fd:
    deps = yaml.safe_load(env_fd)['dependencies']
    for dep in deps:
        if '::' in dep:
            dep = dep.split('::')[1]
        install_requires.append(dep)

git_cmd = ['git', 'remote', 'get-url', 'origin']
git_url = subprocess.check_output(git_cmd, universal_newlines=True).rstrip()

setup(name='conda-shell',
      version=__version__,
      license='BSD',
      description='Port of nix-shell for the conda package manager',
      url=git_url,
      install_requires=install_requires,
      packages=find_packages(),
      zip_safe=False,
      include_package_data=True,
      scripts=['bin/conda-shell'])
