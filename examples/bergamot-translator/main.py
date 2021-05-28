import sys
import os
from copy import deepcopy

basedir = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(basedir, "../../")
sys.path.insert(0, root)

from ghyamlgen import *


def RunIfFailed(job):
  return GitHubExpr("always() && {} == 'failure'".format( "needs.{jobid}.result".format(jobid=job.id())))


def Always(job):
  return GitHubExpr("always()")


def ccache(build, env):
  build = deepcopy(build)
  env = deepcopy(env)

  ccache_cmake_args = '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DCMAKE_C_COMPILER_LAUNCHER=ccache'
  build = [
      CcacheVars(check=GitHubExpr('env.ccache_compilercheck')),
      GHCache(),
      CcacheEnv(
          check=GitHubExpr('env.ccache_compilercheck'),
          base_dir=GitHubExpr('github.workspace'),
          directory=GitHubExpr('env.ccache_dir'),
          compress="true",
          maxsize="50M"),
      CCacheProlog(),
      *build,
      CCacheEpilog(),
  ]

  env.update({
      "ccache_dir":
      QuotedExpr(os.path.join(GitHubExpr('github.workspace'), '.ccache')),
      "ccache_compilercheck": 'content'
      # QuotedExpr(
      #     'bash ${GITHUB_WORKSPACE}/scripts/ci/compiler-hash.sh %compiler%'),
  })

  if "cmake" not in env:
    env["cmake"] = ''
  env["cmake"] += (' ' + ccache_cmake_args)
  return build, env


class MarianBuild:

  def __init__(self, id, name, os, env, setup, build, build_epilog, brt):
    self.id = id
    self.name = name
    self.os = os
    self.env = env
    self.setup = setup
    self.build = build
    self.build_epilog = build_epilog
    self.brt = brt

  def generate(self):
    # Generates two pairs of builds
    def merge(*xs):
      ys = []
      for x in xs:
        if isinstance(x, list):
          ys.extend(x)
        else:
          ys.append(x)
      return ys

    # Two jobs, one with cache, one without
    def CJob(with_cache=False):
      build, env = ccache(self.build, self.env) if with_cache else (self.build,
                                                                    self.env)
      name = self.name
      id = self.id
      if not with_cache:
        id = '{}_fresh'.format(id)
        name = '{} (fresh build)'.format(name)

      return Job(
          id=id,
          name=name,
          env=env,
          runs_on=self.os,
          steps=merge(Checkout(), self.setup, build, self.build_epilog,
                      self.brt))

    cached = CJob(with_cache=True)
    fresh = CJob(with_cache=False)
    fresh.needs(job=cached, OpExpr=RunIfFailed),

    log = Job(
        id='{}_log'.format(self.id),
        name='Log a few contexts',
        env=None,
        runs_on=self.os,
        steps=[
            LogContext('needs'),
            Evaluate("needs.cached.result == 'failure'")
        ])

    log.needs(job=cached, OpExpr=Always)

    jobs = [
        cached,
        # fresh,  
        #log
    ]
    jobdict = {job.id(): job for job in jobs}

    return jobdict


def ubuntu():
  setup = [
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
      ImportedSnippet(
          "Build from source",
          "examples/bergamot-translator/native-ubuntu/20-build.sh",
          working_directory="build"),
  ]

  build_epilog = [
      ImportedSnippet(
          "Print Versions",
          "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
          working_directory='build'),
      ImportedSnippet(
          "Run unit tests",
          "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
          working_directory='build',
          condition=GitHubExpr("{} == 'true'".format('env.unittests'))),
  ]

  envs = {
      "full": {
          "cc": 'gcc-8',
          "cxx": 'g++-8',
          'cmake': '-DCOMPILE_TESTS=on',
          'unittests': "{}".format(GitHubExpr("true")),
          "brt_tags": None,
      },
      "minimal": {
          "cc": 'gcc-8',
          "cxx": 'g++-8',
          'cmake': '-DCOMPILE_TESTS=off -DUSE_WASM_COMPATIBLE_SOURCE=on',
          'brt_tags': QuotedExpr("'#wasm'"),
          'unittests': "{}".format(GitHubExpr("false"))
      }
  }

  # def __init__(self, id, name, env, setup, build_deps, build, build_epilog, brt):
  jobs = {}
  for env_name, env in envs.items():
    platform = {
        "id": "ubuntu_1804_{}".format(env_name),
        "name": "Ubuntu 18.04 {}".format(env_name),
        "os": "ubuntu-18.04"
    }
    variations = MarianBuild(platform["id"], platform["name"], platform["os"],
                             env, setup, build, build_epilog, BRT())
    jobs.update(variations.generate())
  return jobs


def mac():
  setup = [
      ImportedSnippet(
          "Install Dependencies",
          "examples/bergamot-translator/native-mac/00-install-deps.sh"),
      JobShellStep(
          name="Setup BLAS",
          run='\n'.join([
              'echo "LDFLAGS=-L/usr/local/opt/openblas/lib" >> $GITHUB_ENV',
              'echo "CPPFLAGS=-I/usr/local/opt/openblas/include" >> $GITHUB_ENV'
          ]))
  ]

  build = [
      ImportedSnippet(
          "cmake", "examples/bergamot-translator/native-mac/10-cmake-run.sh"),
      JobShellStep(
          name="Build from source", run="make -j2", working_directory="build"),
  ]

  build_epilog = [
      ImportedSnippet(
          "Print Versions",
          "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
          working_directory='build'),
      ImportedSnippet(
          "Run unit tests",
          "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
          working_directory='build',
          condition=GitHubExpr("{} == 'true'".format("env.unittests"))),
  ]

  envs = {
      "full": {
          'cmake': '-DCOMPILE_TESTS=on -DUSE_APPLE_ACCELERATE=off -DUSE_FBGEMM=off -DUSE_STATIC_LIBS=off',
          "brt_tags": QuotedExpr("'#mac'"),
          'unittests': "{}".format(GitHubExpr("true"))
      },
      "minimal": {
          'cmake': '-DCOMPILE_TESTS=off -DUSE_APPLE_ACCELERATE=off -DUSE_FBGEMM=off -DUSE_STATIC_LIBS=on -DUSE_WASM_COMPATIBLE_SOURCE=on',
          'brt_tags': QuotedExpr("'#wasm'"),
          'unittests': "{}".format(GitHubExpr('false'))
      }
  }

  # def __init__(self, id, name, env, setup, build_deps, build, build_epilog, brt):
  jobs = {}
  for env_name, env in envs.items():
    platform = {
        "id": "mac_{}".format(env_name),
        "name": "MacOS {}".format(env_name),
        "os": "macos-10.15"
    }
    variations = MarianBuild(platform["id"], platform["name"], platform["os"],
                             env, setup, build, build_epilog, BRT())
    jobs.update(variations.generate())
  return jobs

def wasm():
  setup = [
      ImportedSnippet(
          "Install Dependencies",
          "examples/bergamot-translator/native-mac/00-install-deps.sh"),
      JobShellStep(
          name="Setup BLAS",
          run='\n'.join([
              'echo "LDFLAGS=-L/usr/local/opt/openblas/lib" >> $GITHUB_ENV',
              'echo "CPPFLAGS=-I/usr/local/opt/openblas/include" >> $GITHUB_ENV'
          ]))
  ]

  build = [
      ImportedSnippet(
          "cmake", "examples/bergamot-translator/native-mac/10-cmake-run.sh"),
      JobShellStep(
          name="Build from source", run="make -j2", working_directory="build"),
  ]

  build_epilog = [
      ImportedSnippet(
          "Print Versions",
          "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
          working_directory='build'),
      ImportedSnippet(
          "Run unit tests",
          "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
          working_directory='build',
          condition=GitHubExpr("{} == 'true'".format("env.unittests"))),
  ]

  envs = {
      "full": {
          'cmake': '-DCOMPILE_TESTS=on -DUSE_APPLE_ACCELERATE=off -DUSE_FBGEMM=off -DUSE_STATIC_LIBS=off',
          "brt_tags": QuotedExpr("'#mac'"),
          'unittests': "{}".format(GitHubExpr("true"))
      },
      "minimal": {
          'cmake': '-DCOMPILE_TESTS=off -DUSE_APPLE_ACCELERATE=off -DUSE_FBGEMM=off -DUSE_STATIC_LIBS=on -DUSE_WASM_COMPATIBLE_SOURCE=on',
          'brt_tags': QuotedExpr("'#wasm'"),
          'unittests': "{}".format(GitHubExpr('false'))
      }
  }

  # def __init__(self, id, name, env, setup, build_deps, build, build_epilog, brt):
  jobs = {}
  for env_name, env in envs.items():
    platform = {
        "id": "mac_{}".format(env_name),
        "name": "MacOS {}".format(env_name),
        "os": "macos-10.15"
    }
    variations = MarianBuild(platform["id"], platform["name"], platform["os"],
                             env, setup, build, build_epilog, BRT())
    jobs.update(variations.generate())
  return jobs


if __name__ == '__main__':
  on = On(push={"branches": ['main']}, pull_request={"branches": ['main']})
  env = {'this_repository': 'browsermt/bergamot-translator'}

  jobs = {}
  jobs.update(ubuntu())
  jobs.update(mac())

  workflow = Workflow(name='default', on=on, env=None, jobs=jobs)
  print(yaml.dump(resolve(workflow), sort_keys=False, width=1024))
