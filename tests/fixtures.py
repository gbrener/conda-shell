import os
import subprocess
import json
import tempfile

import pytest
import six
from conda_shell import main
from conda_shell import conda_cli


@pytest.fixture
def remove_shell_envs():
    """Return a dict of shell environment variables to use with subprocess."""
    # Use an alternate environment prefix to distinguish between the
    # environments only used for testing
    base_env = os.environ.copy()
    base_env['CONDA_SHELL_ENV_PREFIX'] = '__testme_shell_'
    main.DEFAULT_ENV_PREFIX = '__testme_shell_'
    shell_envs_json = subprocess.check_output('conda info --envs --json',
                                              universal_newlines=True,
                                              shell=True)
    shell_envs = filter(lambda dpath: main.is_shell_env(dpath),
                        json.loads(shell_envs_json)['envs'])
    for env_dpath in shell_envs:
        subprocess.check_call('conda env remove -y -p '+env_dpath,
                              universal_newlines=True,
                              shell=True)
    return base_env

@pytest.fixture
def tmp_dir():
    """Create a temporary directory that can be populated by test code.
    Return the tempfile.TemporaryDirectory directory object.
    Directory is automatically removed after the test finishes.
    """
    if six.PY2:
        # Python 2.7 has no tempfile.TemporaryDirectory
        import shutil
        tmpdir_dpath = tempfile.mkdtemp()
        tmpdir = mock.Mock(spec=tempfile.TemporaryDirectory, cleanup=lambda: shutil.rmtree(tmpdir_dpath))
        tmpdir.name = tmpdir_dpath # "name" attr is a special case for Mock
    else:
        tmpdir = tempfile.TemporaryDirectory()
    yield tmpdir
    tmpdir.cleanup()

@pytest.fixture
def cli():
    """Return an instance of conda_shell.conda_cli.CondaShellCLI"""
    # Use an alternate environment prefix to distinguish between the
    # environments only used for testing
    main.DEFAULT_ENV_PREFIX = '__testme_shell_'
    return conda_cli.CondaShellCLI()
