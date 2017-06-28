#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
import os
import re
import subprocess
import uuid
import shlex
import json
import atexit
import cmd

from . import __version__


def rand_env_name():
    return 'shell_' + uuid.uuid4().hex


def parse_script_cmds(script_fpath):
    with open(script_fpath, 'r') as fp:
        for linect, line in enumerate(fp):
            if linect == 0:
                continue
            elif re.match(r'^#!\s*conda-shell\s+', line):
                random_env_name = rand_env_name()
                args = shlex.split(line.split('conda-shell', 1)[1].rstrip())
                # Find interpreter, adjust args list
                interpreter = None
                for argct in range(len(args)):
                    if (args[argct] in ('-i', '--interpeter') and
                            len(args) > argct):
                        interpreter = args[argct+1]
                        args = args[:argct] + args[argct+2:]
                        break
            else:
                break
    install_cmd = ['conda', 'install', '-y', '-n', random_env_name]
    install_cmd.extend(args)
    return install_cmd, interpreter, random_env_name


def get_conda_env_dirs():
    # Sort envs that starts with "shell_" by last-modified time,
    # and return the first one (if any) that match the pkg specs
    conda_info_cmd = ['conda', 'info', '--envs', '--json']
    envs = json.loads(subprocess.check_output(conda_info_cmd,
                                              universal_newlines=True))['envs']
    env_dpaths = sorted(
        filter(
            lambda env: os.path.basename(env).startswith('shell_'),
            envs
        ),
        key=lambda dpath: os.path.getmtime(dpath)
    )
    return env_dpaths


def clean_histline(line):
    conda_install_rgx = r'conda\s+install\s+.*-n shell_\S+ '
    return 'conda install ' + re.split(conda_install_rgx, line, 1)[1].strip()


def env_has_pkgs(env_dpath, install_cmd):
    install_cmdline = clean_histline(' '.join(install_cmd))
    hist_fpath = os.path.join(env_dpath, 'conda-meta', 'history')
    found_install_cmd = False
    with open(hist_fpath, 'r') as fp:
        for line in fp:
            if line.startswith('# cmd: ') and 'conda install' in line:
                found_install_cmd = True
                clean_hist_cmdline = clean_histline(line)
                if clean_hist_cmdline != install_cmdline:
                    return False
    return install_cmd and found_install_cmd


def teardown_env(old_path, old_pstartup):
    os.environ['PATH'] = old_path
    os.environ['PYTHONSTARTUP'] = old_pstartup


def setup_env(env_vars, env_dpath):
    old_path = env_vars['PATH']
    old_pstartup = env_vars['PYTHONSTARTUP']
    atexit.register(teardown_env, old_path, old_pstartup)
    env_vars['PATH'] = os.pathsep.join([os.path.join(env_dpath, 'bin'),
                                        env_vars['PATH']])
    del env_vars['PYTHONSTARTUP']
    return env_vars


class InteractiveShell(cmd.Cmd):
    def __init__(self, prompt, intro=None, env=None):
        super().__init__()
        self.prompt = prompt
        self.intro = ('### conda-shell v'+__version__ if intro is None
                      else intro)
        self.env = (os.environ.copy() if env is None
                    else env)

    def default(self, line):
        if line == 'EOF':
            print('\nExiting conda-shell...')
            return True
        subprocess.call(shlex.split(line.rstrip()),
                        env=self.env,
                        universal_newlines=True)
        return False


def run_cmds_in_env(install_cmd, exec_cmd, env_name, shebang=True, run=None):
    env_vars = os.environ.copy()

    env_dpaths = get_conda_env_dirs()
    for env_dpath in env_dpaths:
        if env_has_pkgs(env_dpath, install_cmd):
            print('Reusing shell env "{}"...'
                  ''.format(os.path.basename(env_dpath)))
            env_vars = setup_env(env_vars, env_dpath)
            if shebang:
                subprocess.check_call(exec_cmd,
                                      env=env_vars,
                                      universal_newlines=True)
            elif run is not None:
                subprocess.check_call(run,
                                      env=env_vars,
                                      universal_newlines=True)
            else:
                prompt = '[{}]: '.format(os.path.basename(env_dpath))
                InteractiveShell(prompt, env=env_vars).cmdloop()
            return

    # Existing environment was not found, so create a fresh one
    subprocess.check_call(['conda', 'create', '-y', '-n', env_name],
                          universal_newlines=True)
    subprocess.check_call(install_cmd,
                          universal_newlines=True)
    found_env = False
    env_dpaths = get_conda_env_dirs()
    for env_dpath in env_dpaths:
        if env_dpath.endswith(env_name):
            env_vars = setup_env(env_vars, env_dpath)
            found_env = True
            break
    if not found_env:
        raise ValueError('Could not find freshly-created environment named "{}'
                         '"'.format(env_name))
    if shebang:
        subprocess.check_call(exec_cmd,
                              env=env_vars,
                              universal_newlines=True)
    elif run is not None:
        subprocess.check_call(run,
                              env=env_vars,
                              universal_newlines=True)
    else:
        prompt = '[{}]: '.format(os.path.basename(env_dpath))
        InteractiveShell(prompt, env=env_vars).cmdloop()


def main(argv):
    in_shebang = (len(argv) > 1 and
                  argv[0].endswith('conda-shell') and
                  os.path.isfile(argv[1]) and
                  os.access(argv[1], os.X_OK))
    run_cmd = None

    if in_shebang:
        script_fpath = argv[1]
        install_cmd, interpreter, random_env_name = parse_script_cmds(
            script_fpath,
        )
        if interpreter is None:
            raise ValueError('When called from a shebang line, please provide'
                             'the --interpeter (or -i) argument to'
                             'conda-shell')
        exec_cmd = [interpreter, script_fpath]
        exec_cmd.extend(argv[2:])
    else:
        if not argv[1:]:
            raise ValueError('No arguments provided.')

        random_env_name = rand_env_name()
        install_cmd = ['conda', 'install', '-y', '-n', random_env_name]
        install_cmd.extend(argv[1:])
        exec_cmd = []

        for partct, part in enumerate(install_cmd):
            if part == '--run':
                run_cmd = install_cmd[partct+1]
                break
        if run_cmd is not None:
            install_cmd.remove('--run')
            install_cmd.remove(run_cmd)
            run_cmd = shlex.split(run_cmd)

    run_cmds_in_env(install_cmd, exec_cmd, random_env_name,
                    shebang=in_shebang,
                    run=run_cmd)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
