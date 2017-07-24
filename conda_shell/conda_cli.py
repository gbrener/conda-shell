"""
Wrap portions of conda's command-line interface.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys
import importlib
import argparse
import copy
import glob

import six
if six.PY2:
    import mock
else:
    from unittest import mock


class CondaShellArgumentError(Exception):
    pass


class CondaCLI(object):
    """Python wrapper for conda's command line interface.
    This enables us to call `conda` without using subprocess.

    It also offers conveniences such as modifying the argparse help output,
    and modifying the CLI as needed for conda-shell.

    Limitations:
        - current only supports 'conda install' and 'conda create'
    """

    def __init__(self):
        """Constructor."""
        # Extend sys.path so that conda.cli module can be imported, then import
        # conda's CLI modules.
        self.conda_sp_dpath = self._get_conda_sp_dpath()
        (self._base_mod,
         self._main_mod,
         self._main_install_mod,
         self._main_create_mod) = self._import_conda_modules()

        self._create_parser, self._install_parser = None, None
        parser, sub_parsers = self._main_mod.generate_parser()
        self._main_install_mod.configure_parser(sub_parsers)
        self._main_create_mod.configure_parser(sub_parsers)

        subparsers_action = None
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break
        action_parser_map = subparsers_action._name_parser_map
        if 'install' in action_parser_map:
            self._install_parser = action_parser_map['install']
            # These arguments are somehow dropped from the Namespace
            self._install_parser.add_argument('--no-default-packages',
                                              default=False)
            self._install_parser.add_argument('--clone', default=False)
        if 'create' in action_parser_map:
            self._create_parser = action_parser_map['create']
        # Additional branches may be added here to support more of conda's
        # subparsers

    def _get_conda_sp_dpath(self):
        """Return the site-packages directory where conda resides.
        Errors-out if the user isn't using Python from within conda.
        """
        if 'conda' not in sys.executable:
            raise ValueError('Failed to find directory where conda is'
                             ' installed. conda-shell expects to find conda'
                             ' installed in a directory with "conda" in the'
                             ' name.')

        conda_install_dpath = sys.executable.split('conda')[0] + 'conda'
        conda_sp_dpath = None
        installed_libs = os.path.join(conda_install_dpath, 'lib')
        for root, dirnames, filenames in os.walk(installed_libs, topdown=True):
            idx = 0
            while idx < len(dirnames):
                dirname = dirnames[idx]
                if not (dirname.startswith('python') or
                        dirname == 'site-packages'):
                    if root.endswith('site-packages') and dirname == 'conda':
                        conda_sp_dpath = root
                        break
                    dirnames.remove(dirname)
                    idx -= 1
                idx += 1
            if conda_sp_dpath is not None:
                break
        if conda_sp_dpath is None:
            raise ValueError('Failed to find site-packages directory where'
                             ' conda is installed.')
        return conda_sp_dpath

    def _import_conda_modules(self):
        """Import the necessary conda modules.
        """
        sys.path.append(self.conda_sp_dpath)
        sys.path.extend(glob.glob(os.path.join(self.conda_sp_dpath, 'pycosat*')))

        for modname in ('ruamel', 'ruamel.yaml', 'ruamel.yaml.comments',
                        'ruamel.yaml.scanner'):
            sys.modules[modname] = mock.MagicMock()

        imported_modules = (
            importlib.import_module('conda.base'),
            importlib.import_module('conda.cli.main'),
            importlib.import_module('conda.cli.main_install'),
            importlib.import_module('conda.cli.main_create'),
        )

        return imported_modules

    def parse_create_args(self, argv):
        """Given a list of arguments (likely derived from `sys.argv`), return
        argparse output as if `conda create` were called over the command line.
        """
        known, unknown = self._create_parser.parse_known_args(argv)
        if ((set(['-i', '--interpreter']) - set(unknown)) not in
            (set(['--interpreter']), set(['-i']))):
            self._create_parser.parse_args(argv)
        return known

    def parse_install_args(self, argv):
        """Given a list of arguments (likely derived from `sys.argv`), return
        argparse output as if `conda install` were called over the command
        line.
        """
        known, unknown = self._install_parser.parse_known_args(argv)
        return known

    def conda_create(self, args):
        """Given a Namespace object from `conda create`'s argument parser,
        return the output from the `conda create` command (this may be `None`).
        """
        prefix = os.path.join(os.path.split(os.path.split(os.path.split(self.conda_sp_dpath)[0])[0])[0], 'envs', args.name)
        # The following is needed to satisfy conda Context object
        self._base_mod.context.context.always_yes = True
        self._base_mod.context.get_prefix = lambda *args, **kwargs: prefix
        with mock.patch('conda.history.sys') as sys_mock:
            sys_mock.argv = []
            skip_args = 0
            for arg in args._argv:
                if skip_args:
                    skip_args -= 1
                elif arg == 'conda-shell':
                    sys_mock.argv.append('conda')
                    sys_mock.argv.append('create')
                elif arg == '--run':
                    skip_args = 1
                else:
                    sys_mock.argv.append(arg)
            retval = self._main_create_mod.execute(args, self._create_parser)
        return retval

    def conda_install(self, args):
        """Given a Namespace object from `conda install`'s argument parser,
        return the output from the `conda install` command (this may be
        `None`).
        """
        prefix = os.path.join(os.path.split(os.path.split(os.path.split(self.conda_sp_dpath)[0])[0])[0], 'envs', args.name)
        # The following is needed to satisfy conda Context object
        self._base_mod.context.context.always_yes = True
        self._base_mod.context.get_prefix = lambda *args, **kwargs: prefix
        with mock.patch('conda.history.sys') as sys_mock:
            sys_mock.argv = []
            skip_args = 0
            for arg in args._argv:
                if skip_args:
                    skip_args -= 1
                elif arg == 'conda-shell':
                    sys_mock.argv.append('conda')
                    sys_mock.argv.append('install')
                elif arg in ('-i', '--interpreter'):
                    skip_args = 0
                else:
                    sys_mock.argv.append(arg)
            retval = self._main_install_mod.execute(args, self._install_parser)
        return retval


class CondaShellCLI(CondaCLI):
    """Reuse conda's CLI, but modify as needed for conda-shell's purposes.

    Besides modifying the `--help` output, this adds the following arguments:
        - `--run`: For running arbitrary commands in conda environments made by
          conda-shell
        - `-i` / `--interpreter`: For providing an interpreter via a shebang
  
        line
    """

    def __init__(self):
        super(CondaShellCLI, self).__init__()

        # Modify --help output
        self._shell_parser = copy.copy(self._install_parser)
        self._shell_parser.prog = 'conda-shell'
        self._shell_parser.epilog = """Examples:
    conda-shell python=3.6 numpy=1.13
    conda-shell python=2.7 --run 'python -V'
"""
        self._shell_parser.description = """Port of the `nix-shell` command for the conda package manager.

This is a superset of the command-line interface for
`conda install`; execute `conda install --help` for more information.
"""
        # Create additional arguments for conda-shell
        mux_group = self._shell_parser.add_mutually_exclusive_group()
        mux_group.add_argument('--run', type=str,
                               help='Command to run inside of the temporary'
                                    'conda environment')
        mux_group.add_argument('-i', '--interpreter', type=str,
                               help='')

    def parse_shell_args(self, argv):
        """Given a list of arguments (likely derived from `sys.argv`), return
        argparse output as if `conda-shell` were called over the command line.
        """
        return self._shell_parser.parse_args(argv)
