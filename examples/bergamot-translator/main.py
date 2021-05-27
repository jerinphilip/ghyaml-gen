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

  job1 = Job(
      name='job1',
      runs_on='ubuntu-16.04',
      steps=[
          Checkout(),
          ImportedSnippet(
              "Install Dependencies",
              "examples/bergamot-translator/native-ubuntu/00-install-deps.sh"),
          ImportedSnippet(
              "Install MKL",
              "examples/bergamot-translator/native-ubuntu/01-install-mkl.sh"),
          CcacheVars(check=GitHubExpr('matrix.cmd')),
          CcacheEnv(),
          CCacheProlog(),
          ImportedSnippet(
              "cmake",
              "examples/bergamot-translator/native-ubuntu/10-cmake-run.sh"),
          ImportedSnippet(
              "Build from source",
              "examples/bergamot-translator/native-ubuntu/20-build.sh"),
          CCacheEpilog(),
          ImportedSnippet(
              "Print Versions",
              "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
              working_directory='build'),
          ImportedSnippet(
              "Run unit tests",
              "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
              working_directory='build'),
          *BRT(),
      ])

  job2 = Job(
      name='job2',
      needs=Needs(job=job1, result='success'),
      runs_on='ubuntu-16.04',
      steps=[
          Checkout(),
          ImportedSnippet(
              "Install Dependencies",
              "examples/bergamot-translator/native-ubuntu/00-install-deps.sh"),
          ImportedSnippet(
              "Install MKL",
              "examples/bergamot-translator/native-ubuntu/01-install-mkl.sh"),
          CcacheVars(check='${{matrix.cmd}}'),
          CcacheEnv(),
          CCacheProlog(),
          ImportedSnippet(
              "cmake",
              "examples/bergamot-translator/native-ubuntu/10-cmake-run.sh"),
          ImportedSnippet(
              "Build from source",
              "examples/bergamot-translator/native-ubuntu/20-build.sh"),
          CCacheEpilog(),
          ImportedSnippet(
              "Print Versions",
              "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
              working_directory='build'),
          ImportedSnippet(
              "Run unit tests",
              "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
              working_directory='build'),
          *BRT(),
      ])




  jobs = {"job1": job1, "job2" :job2}
  workflow = Workflow(name='default', on=on, env=env, jobs=jobs)
  print(yaml.dump(resolve(workflow), sort_keys=False))
