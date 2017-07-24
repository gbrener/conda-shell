import subprocess
import json

import pytest
from conda_shell import main
from conda_shell import conda_cli


@pytest.fixture
def remove_shell_envs():
    # Use an alternate environment prefix to distinguish between the
    # environments only used for testing
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


@pytest.fixture
def cli():
    # Use an alternate environment prefix to distinguish between the
    # environments only used for testing
    main.DEFAULT_ENV_PREFIX = '__testme_shell_'
    return conda_cli.CondaShellCLI()
