"""
Support for interactive conda environments.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
import atexit
import cmd
import subprocess
import shlex

import six

from . import __version__


def teardown_env(old_path, old_pstartup):
    os.environ['PATH'] = old_path
    os.environ['PYTHONSTARTUP'] = old_pstartup


def setup_env(env_vars, env_dpath):
    old_path = env_vars.get('PATH', '')
    old_pstartup = env_vars.get('PYTHONSTARTUP', '')
    atexit.register(teardown_env, old_path, old_pstartup)
    env_bindir = os.path.join(env_dpath, 'bin')
    env_vars['PATH'] = os.pathsep.join([env_bindir, old_path])
    if 'PYTHONSTARTUP' in env_vars:
        del env_vars['PYTHONSTARTUP']
    return env_vars


class InteractiveShell(cmd.Cmd):
    def __init__(self, prompt, intro=None, env=None):
        if six.PY2:
            cmd.Cmd.__init__(self)
        else:
            super(InteractiveShell, self).__init__()
        self.prompt = prompt
        self.intro = ('### conda-shell v'+__version__ if intro is None
                      else intro)
        self.env = (os.environ.copy() if env is None
                    else env)

    def default(self, line):  # pragma: no cover
        if line == 'EOF':
            print('\nExiting conda-shell...', file=sys.stderr)
            return True
        subprocess.call(shlex.split(line.rstrip()),
                        env=self.env,
                        universal_newlines=True)
        return False
