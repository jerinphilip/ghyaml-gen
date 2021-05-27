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

class YAMLRenderable: pass

class On(YAMLRenderable):
    def __init__(self, push=None, pull_request=None, schedule=None):
        self.fields = {
            "push": push,
            "pull_request": pull_request,
            "schedule": schedule
        }

class Workflow(YAMLRenderable):
    def __init__(self, name, on, env=None, jobs=None):
        self.fields = {
            "name": name,
            "on": on,
            "env": env,
            "jobs": jobs
        }

class Job(YAMLRenderable):
    def __init__(self, name, runs_on, outputs=None, condition=None, steps=None, needs=None):
        self.fields = {
            "name": name,
            "needs": needs,
            "runs-on": runs_on,
            "outputs": outputs,
            "if": condition,
            "steps": steps
        }

class Checkout(YAMLRenderable):
    def __init__(self):
        self.fields = {
            "name": "Checkout",
            "uses": "actions/checkout@v2",
            "with": {
                "submodules": "recursive"
            }
        }

class ImportedSnippet(YAMLRenderable):
    def __init__(self, name, fpath):
        contents = None
        with open(fpath) as fp:
            contents = fp.read()

        self.fields = {
            "name": name,
            "run": Snippet(contents)
        }

def resolve(cls):
    native = None
    if isinstance(cls, YAMLRenderable):
        native = resolve(cls.fields)

    elif isinstance(cls, list):
        native = [ resolve(v) for v in cls if v is not None]

    elif isinstance(cls, dict):
        native = { k: resolve(v)  for k, v in cls.items() if v is not None}

    else:
        native = cls

    return native



if __name__ == '__main__':
    on = On(push={"branches": ['main']}, pull_request={ "branches": ['main']})
    env = dict([
            ('this_repository', 'browsermt/bergamot-translator')
    ])

    job1 = Job(name='job1',
            runs_on='ubuntu-16.04',
            steps=[
                Checkout(),
                ImportedSnippet("Install Dependencies", "examples/bergamot-translator/native-ubuntu/00-install-deps.sh")
            ]
            
    )

    jobs = {"job1": job1}
    workflow = Workflow(name='default', on=on, env=env, jobs=jobs)
    print(yaml.dump(resolve(workflow), sort_keys=False))
