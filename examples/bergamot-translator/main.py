import sys
import os

basedir = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(basedir, "../../")
print(root)
sys.path.insert(0, root)

from ghyamlgen import *

if __name__ == '__main__':
  on = On(push={"branches": ['main']}, pull_request={"branches": ['main']})
  env = {'this_repository': 'browsermt/bergamot-translator'}

  setup = [
      Checkout(),
      ImportedSnippet(
          "Install Dependencies",
          "examples/bergamot-translator/native-ubuntu/00-install-deps.sh"),
      ImportedSnippet(
          "Install MKL",
          "examples/bergamot-translator/native-ubuntu/01-install-mkl.sh"),
  ]

  build = [
      ImportedSnippet(
          "cmake",
          "examples/bergamot-translator/native-ubuntu/10-cmake-run.sh"),
      ImportedSnippet("Build from source",
                      "examples/bergamot-translator/native-ubuntu/20-build.sh"),
  ]

  def ccache(build):
    return [
        CcacheVars(check=GitHubExpr('matrix.cmd')),
        CcacheEnv(),
        CCacheProlog(),
        *build,
        CCacheEpilog(),
    ]

  build_epilog = [
      ImportedSnippet(
          "Print Versions",
          "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
          working_directory='build'),
      ImportedSnippet(
          "Run unit tests",
          "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
          working_directory='build'),
  ]

  def merge(*xs):
    ys = []
    for x in xs:
      ys.extend(x)
    return ys

  job1 = Job(name='job1',
             runs_on='ubuntu-16.04',
             steps=merge(setup, ccache(build), build_epilog, BRT()))

  job2 = Job(name='job2',
             needs=Needs(job=job1, result='success'),
             runs_on='ubuntu-16.04',
             steps=merge(setup, build, build_epilog, BRT()))

  jobs = {"job1": job1, "job2": job2}
  workflow = Workflow(name='default', on=on, env=env, jobs=jobs)
  print(yaml.dump(resolve(workflow), sort_keys=False))
