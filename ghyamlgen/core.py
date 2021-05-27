# This is in the end YAML, I'm changing the matrix generation, parameterized by
# my own set of matrix parameters. In addition, I'm adding my own set of
# conditionals, which translates to github's ifs.

from abc import ABC, abstractmethod
from collections import OrderedDict
import typing as t
import sys
import yaml
from dataclasses import dataclass, field

class Snippet(str):
  @staticmethod
  def representer(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
      return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(Snippet, Snippet.representer)

class GitHubExpr(str):
  def __new__(cls, value):
      value = '${{ ' + value + ' }}'
      return str.__new__(cls, value)

  @staticmethod
  def representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(GitHubExpr, GitHubExpr.representer)

class YAMLRenderable:
    pass

class On(YAMLRenderable):
  def __init__(self, push=None, pull_request=None, schedule=None):
    self.fields = {
        "push": push,
        "pull_request": pull_request,
        "schedule": schedule
    }

class Workflow(YAMLRenderable):

  def __init__(self, name, on, env=None, jobs=None):
    self.fields = {"name": name, "on": on, "env": env, "jobs": jobs}


class Needs(YAMLRenderable):
    def __init__(self, job, result=None):
        suffix = '' if result is None else '== {}'.format(result)
        condition = "needs.{jobname}.result {suffix}".format(jobname = job.fields["name"], suffix = suffix)
        self.fields = {
            "needs": job.fields["needs"],
            "if": GitHubExpr(condition)
        }


class Job(YAMLRenderable):
  def __init__(self,
               name,
               runs_on,
               outputs=None,
               condition=None,
               steps=None,
               needs=None):

    condition = None if needs is None else needs.fields["if"]
    needed_job = None if needs is None else needs.fields["needs"]

    self.fields = {
        "name": name,
        "needs": needs,
        "runs-on": runs_on,
        "outputs": outputs,
        "if": condition,
        "steps": steps,
        "needs": needed_job,
    }

class Group(YAMLRenderable):
    def __init__(self, *renderables):
        self.renderables = renderables


class Checkout(YAMLRenderable):

  def __init__(self):
    self.fields = {
        "name": "Checkout",
        "uses": "actions/checkout@v2",
        "with": {
            "submodules": "recursive"
        }
    }


class JobShellStep(YAMLRenderable):

  def __init__(self, name, run, working_directory=None, shell=None, id=None):
    self.fields = {
        "name": name,
        "working-directory": working_directory,
        "shell": shell,
        "id": id,
        "run": Snippet(run) if '\n' in run else run,
    }


class BRT(list):

  def __init__(self, working_directory='bergamot-translator-tests'):
    super().__init__([
        JobShellStep(
            name="Install regression-test framework (BRT)",
            working_directory=working_directory,
            run="make install"),
        JobShellStep(
            name="Run regression-tests (BRT)",
            working_directory=working_directory,
            run="MARIAN=../build ./run_brt.sh ${{ matrix.test_tags }}")
    ])


class ImportedSnippet(JobShellStep):

  def __init__(self, name, fpath, working_directory=None):
    contents = None
    with open(fpath) as fp:
      contents = fp.read().strip()
    super().__init__(name=name, run=contents, working_directory=working_directory)


def resolve(cls):
  native = None
  if isinstance(cls, YAMLRenderable):
    native = resolve(cls.fields)

  elif isinstance(cls, list):
    native = [resolve(v) for v in cls if v is not None]

  elif isinstance(cls, dict):
    native = {k: resolve(v) for k, v in cls.items() if v is not None}

  else:
    native = cls

  return native


class CcacheEnv(JobShellStep):

  def __init__(self,
               check=None,
               base_dir=None,
               directory=None,
               compress=None,
               maxsize=None):
    env = {
        'COMPILER_CHECK': check,
        'BASE_DIR': base_dir,
        'COMPRESS': compress,
        'DIR': directory,
        'MAXSIZE': maxsize
    }

    commands = [
        'echo "CCACHE_{key}={value}" >> $GITHUB_ENV'.format(
            key=key, value=value) for key, value in env.items()
    ]

    run = '\n'.join(commands)
    super().__init__(name="ccache environment setup", run=run)


class CcacheVars(JobShellStep):

  def __init__(self, check):
    ccache_vars = {"hash": check, "timestamp": "date '+%Y-%m-%dT%H.%M.%S'"}
    commands = [
        'echo "::set-output name={key}::$({evalExpr})'.format(
            key=key, evalExpr=evalExpr)
        for key, evalExpr in ccache_vars.items()
    ]

    super().__init__(
        name="Generate ccache_vars for ccache based on machine",
        run='\n'.join(commands),
        id="ccache_vars",
        shell="bash"
    )

class CCacheProlog(JobShellStep):
    def __init__(self):
        commands = [
            'ccache -s # Print current cache stats',
            'ccache -z # Zero cache entry',
        ]
        super().__init__(name="ccache prolog", run = '\n'.join(commands))

class CCacheEpilog(JobShellStep):
    def __init__(self):
        commands = [
            'ccache -s # Print current cache stats',
        ]
        super().__init__(name="ccache epilog", run = '\n'.join(commands))

