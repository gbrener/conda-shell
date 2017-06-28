# conda-shell

Port of the `nix-shell` command for the [conda package manager](https://github.com/conda/conda). Nix-shell is a part of the [nix package manager](https://github.com/NixOS/nix).

**Note: `conda-shell` is still in _alpha_. GitHub issues (bug reports, feature requests, etc) and PRs are welcome!**

## Purpose

In a nutshell (pun intended), conda-shell has the following goals:

    - Make conda environments as "cheap" as possible to create and reuse
    - Treat conda environments in a similar fashion to containers, i.e.
        - Enable execution of arbitrary commands in a predefined environment, or
        - Activate an environment as an interactive subshell
    - Maintain feature-parity with nix-shell, to the extent that conda supports it

Some auxillary benefits:

    - Distribute a single script (including its versioned dependencies), without creating a conda package nor an environment.yml
    - No need to memorize the names of your "throwaway" conda environments
    - No need to type `source activate ...` and `source deactivate`
    - Quickly find and activate existing environments based on package specs

## Installation

### With `conda`

Assuming [Miniconda or Anaconda (aka "conda")](https://conda.io/docs/install/quick.html) is installed, type:

```
conda install -c gbrener conda-shell
```

### From source

```
git clone https://github.com/gbrener/conda-shell.git
cd conda-shell
conda env create -f requirements.txt -n conda-shell
source activate conda-shell # Activate dev environment
python setup.py install
```

To deactivate the dev environment, type `source deactivate`.

## Usage

`conda-shell` can be used in three contexts:

    - Running arbitrary commands in a conda environment
    - Starting an interactive shell inside of a conda environment
    - Using `conda-shell` inside a script

The following examples assume a desired environment of `Python 3.6` and `NumPy 1.13`.

### Arbitrary commands

Here we run Python code inside of the environment:
```
conda-shell python=3.6 numpy=1.13 --run 'python -c "import numpy as np; print(np.__version__)"'
```

With the same dependencies, this time a script:
```
conda-shell python=3.6 numpy=1.13 --run 'python helloworld.py'
```

Note that the second command reuses the conda environment created in the first command.

### Interactive Shell

Without the `--run` parameter, an interactive shell prompt appears:

```
conda-shell python=3.6 numpy=1.13
...
### conda-shell v0.0.1.dev1
[shell_abc]: 
```

A similar effect could be acheived with the following `conda` commands:

```
conda create -n shell_abc python=3.6 numpy=1.13
source activate shell_abc
```

One advantage of using `conda-shell` here is that you wouldn't need to memorize the new environment's name; `conda-shell` would find it automatically based on the dependencies. Also, exiting the `conda-shell` environment automatically deactivates it, saving you two `source` commands.

### Shebang

Create a file called `np-ver-check.py`:

```
#!/usr/bin/env conda-shell
#!conda-shell -i python python=3.6 numpy=1.13

import numpy as np

print(np.__version__)
```

Then make the script executable:

```
chmod +x np-ver-check.py
```

Finally, run it and watch `conda-shell` go!

```
./np-ver-check.py
```

## FAQ

Q: Have you seen [conda-execute](https://github.com/conda-tools/conda-execute)?
A: On the surface, `conda-shell` may look like it offers very similar features as `conda-execute`. However there are a number of key differences:
    - `conda-shell` has different goals than `conda-execute` (see above)
    - Syntactically, `conda-shell`'s use of the [shebang line]() (borrowed from `nix-shell`'s syntax) is more terse and reuses the CLI from `conda install`. We avoid inventing (and maintaining) a new YAML-based syntax for declaring package dependencies
    - `conda-shell` does not need to be installed into the root environment
    - `conda-shell` offers container-like features, such as executing arbitrary commands and acting as an interactive subshell

Q: Why is this not a part of `conda` (like `nix-shell` is a part of `nix`)?
A: First of all, `conda-shell` is still a very immature tool. Second, `conda-shell` is not (yet?) compatible with Windows.
