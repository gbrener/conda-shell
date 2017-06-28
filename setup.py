import subprocess

from setuptools import setup, find_packages


with open('VERSION') as ver_fd:
    version = ver_fd.read().strip()

with open('requirements.txt') as reqs_fd:
    install_requires = reqs_fd.read().strip().split()

git_cmd = ['git', 'remote', 'get-url', 'origin']
git_url = subprocess.check_output(git_cmd).rstrip()

setup(name='conda-shell',
      version=version,
      description='Port of nix-shell for the conda package manager',
      url=git_url,
      install_requires=install_requires,
      packages=find_packages(),
      zip_safe=False,
      include_package_data=True,
      scripts=['bin/conda-shell'])
