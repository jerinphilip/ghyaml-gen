import sys
import os
from copy import deepcopy

basedir = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(basedir, "../../")
sys.path.insert(0, root)

from ghyamlgen import *


def merge(*xs):
  ys = []
  for x in xs:
    if isinstance(x, list):
      ys.extend(x)
    else:
      ys.append(x)
  return ys


def ccache(build):
  build = deepcopy(build)

  def build_ccache_config():
    f = lambda x: GitHubExpr(GitHubMapping(x, context='env'))
    ccache_config = {
        "keys": [
            # GitHubExpr('github.job'),
            GitHubExpr('matrix.identifier'),
            GitHubExpr('steps.ccache_vars.outputs.hash'),
            GitHubExpr('github.ref'),
            GitHubExpr('steps.ccache_vars.outputs.timestamp')
        ],
        "compilercheck":
        f("ccache_compilercheck"),
        "basedir": f("ccache_basedir"),
        "dir":
        f("ccache_dir"),
        "compress":
        f("ccache_compress"),
        "compresslevel": f("ccache_compresslevel"),
        "maxsize":
        f("ccache_maxsize"),
        "is_command":
        False
    }
    return ccache_config

  config = build_ccache_config()
  build = [
      CcacheVars(config["compilercheck"], cmd=config["is_command"]),
      GHCache(config["keys"], config["dir"]),
      CcacheEnv(config),
      CCacheProlog(),
      *build,
      CCacheEpilog(),
  ]

  return build


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

  def constructJob(self, with_cache=False):
    build = ccache(self.build) if with_cache else self.build
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
        steps=merge(Checkout(), self.setup, build, self.build_epilog, self.brt))

  def constructMatrixJob(self, matrix, with_cache=False):
    build = ccache(self.build) if with_cache else self.build
    # name = self.name
    id = self.id
    if not with_cache:
      id = '{}_fresh'.format(id)
      # name = '{} (fresh build)'.format(name)
    steps = merge(Checkout(), self.setup, build, self.build_epilog, self.brt)

    return MatrixJob(id=id, matrix=matrix, steps=steps)

  def generate(self):
    # Two jobs, one with cache, one without
    cached = self.constructJob(with_cache=True)
    fresh = self.constructJob(with_cache=False)
    return {cached.id(): cached}
    # return cached_flow(cached, fresh)


def cached_flow(cached: Job, fresh: Job):
  fresh.needs(job=cached, OpExpr=RunIfFailed),
  log = Job(
      id='{}_log'.format(self.id),
      name='Log a few contexts',
      env=None,
      runs_on=self.os,
      steps=[LogContext('needs'),
             Evaluate("needs.cached.result == 'failure'")])

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

  def build_epilog(context):
    return [
        ImportedSnippet(
            "Print Versions",
            "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
            working_directory='build'),
        ImportedSnippet(
            "Run unit tests",
            "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
            working_directory='build',
            condition=GitHubExpr("{} == 'true'".format(
                GitHubMapping('unittests', context=context)))),
    ]

  configs = {
      "full": {
          'cmake': '-DCOMPILE_TESTS=on',
          'unittests': 'true',
          "brt_tags": '',
      },
      "minimal": {
          'cmake': '-DCOMPILE_TESTS=off -DUSE_WASM_COMPATIBLE_SOURCE=on',
          'unittests': 'false',
          'brt_tags': QuotedExpr("'#wasm'"),
      }
  }

  matrix = {"include": []}

  def platform_ubuntu(version, env_name):
    platform = {
        "id": "ubuntu_{}_{}".format(version.replace('.', ''), env_name),
        "name": "Ubuntu {} {}".format(version, env_name),
        "os": "ubuntu-{}".format(version)
    }
    return platform

  for version in ['18.04', '20.04']:
    for env_name, env in configs.items():
      platform = platform_ubuntu(version, env_name)
      matrix["include"].append({
          "name": platform["name"],
          "os": platform["os"],
          "identifier": platform["id"],
          "cmake": env["cmake"],
          "brt_tags": env["brt_tags"],
          "unittests": env["unittests"]
      })

  # print(yaml.dump(matrix, sort_keys=False))

  def build_env_jobs():
    jobs = {}
    for version in ['18.04', '20.04']:
      for env_name, env in configs.items():
        platform = platform_ubuntu(version, env_name)
        tags = GitHubExpr(GitHubMapping('brt_tags', context='env'))
        jobid = GitHubExpr(GitHubMapping('job', context='github'))

        # env = None
        variations = MarianBuild(
            platform["id"],
            platform["name"],
            platform["os"],
            env,
            setup,
            build,
            build_epilog(context='env'),
            BRT(jobid, tags))
        jobs.update(variations.generate())
    return jobs

  def build_matrix_jobs(matrix):
    name = GitHubExpr(GitHubMapping('name', context='matrix'))
    os = GitHubExpr(GitHubMapping('os', context='matrix'))
    env = None
    jobid = GitHubExpr(GitHubMapping('identifier', context='matrix'))
    tags = GitHubExpr(GitHubMapping('brt_tags', context='matrix'))
    matrix_build = MarianBuild(
        "ubuntu",
        name,
        os,
        env,
        setup,
        build,
        build_epilog(context='matrix'),
        BRT(jobid, tags))
    matrix_job = matrix_build.constructMatrixJob(matrix, with_cache=True)
    return {matrix_job.id(): matrix_job}

  return build_matrix_jobs(matrix)


def mac():
  setup = [
      ImportedSnippet(
          "Install Dependencies",
          "examples/bergamot-translator/native-mac/00-install-deps.sh"),
      JobShellStep(
          name="Setup path with gnu",
          run='\n'.join([
              'echo "/usr/local/opt/coreutils/libexec/gnubin" >> $GITHUB_PATH',
              'echo "/usr/local/opt/findutils/libexec/gnubin" >> $GITHUB_PATH'
          ])),
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

  def build_epilog(context):
    build_epilog = [
        ImportedSnippet(
            "Print Versions",
            "examples/bergamot-translator/native-ubuntu/21-print-versions.sh",
            working_directory='build'),
        ImportedSnippet(
            "Run unit tests",
            "examples/bergamot-translator/native-ubuntu/30-unit-tests.sh",
            working_directory='build',
            condition=GitHubExpr("{} == 'true'".format(
                GitHubMapping('unittests', context=context)))),
    ]
    return build_epilog

  configs = {
      "full": {
          'cmake':
          '-DCOMPILE_TESTS=on -DUSE_APPLE_ACCELERATE=off -DUSE_FBGEMM=off -DUSE_STATIC_LIBS=off',
          "brt_tags":
          QuotedExpr("'#mac'"),
          'unittests':
          'true',
      },
      "minimal": {
          'cmake':
          '-DCOMPILE_TESTS=off -DUSE_APPLE_ACCELERATE=off -DUSE_FBGEMM=off -DUSE_STATIC_LIBS=on -DUSE_WASM_COMPATIBLE_SOURCE=on',
          'brt_tags':
          QuotedExpr("'#wasm'"),
          'unittests':
          'false',
      }
  }

  matrix = {"include": []}

  def platform_mac(version, env_name):
    version_identifier = version.replace('.', '')
    platform = {
        "id": "mac_{}_{}".format(version_identifier, env_name),
        "name": "MacOS {} {}".format(version, env_name),
        "os": "macos-{}".format(version)
    }
    return platform

  for version in ['10.15']:
    for env_name, env in configs.items():
      platform = platform_mac(version, env_name)
      matrix["include"].append({
          "name": platform["name"],
          "os": platform["os"],
          "identifier": platform["id"],
          "cmake": env["cmake"],
          "brt_tags": env["brt_tags"],
          "unittests": env["unittests"]
      })

  def build_matrix_jobs(matrix):
    name = GitHubExpr(GitHubMapping('name', context='matrix'))
    os = GitHubExpr(GitHubMapping('os', context='matrix'))
    env = None
    jobid = GitHubExpr(GitHubMapping('identifier', context='matrix'))
    tags = GitHubExpr(GitHubMapping('brt_tags', context='matrix'))
    matrix_build = MarianBuild(
        "mac",
        name,
        os,
        env,
        setup,
        build,
        build_epilog(context='matrix'),
        BRT(jobid, tags))
    matrix_job = matrix_build.constructMatrixJob(matrix, with_cache=True)
    return {matrix_job.id(): matrix_job}

  # def __init__(self, id, name, env, setup, build_deps, build, build_epilog, brt):
  def build_env_job():
    jobs = {}
    for env_name, env in configs.items():
      tags = GitHubExpr(GitHubMapping('brt_tags', context='env'))
      jobid = GitHubExpr(GitHubMapping('job', context='github'))
      variations = MarianBuild(platform["id"], platform["name"],
                               platform["os"], env, setup, build, build_epilog,
                               BRT(jobid, tags))
      jobs.update(variations.generate())
    return jobs

  return build_matrix_jobs(matrix)


if __name__ == '__main__':
  on = On(push={"branches": ['main']}, pull_request={"branches": ['main']})
  # on = On(push={"branches": ['main']}, workflow_dispatch={
  #     "inputs": {
  #           "commit_sha": {
  #               "description": "SHA of the commit you want to trigger a build for",
  #               "required": True
  #           }
  #       }
  #     })
  env = ({
      "ccache_basedir":
      GitHubExpr(GitHubMapping('workspace', context='github')),
      "ccache_dir":
      QuotedExpr(
          os.path.join(
              GitHubExpr(GitHubMapping('workspace', context='github')),
              '.ccache')),
      "ccache_compilercheck":
      'content',
      "ccache_compress":
      "true",
      "ccache_compresslevel": 9,
      "ccache_maxsize":
      "200M",
      # QuotedExpr(
      #     'bash ${GITHUB_WORKSPACE}/scripts/ci/compiler-hash.sh %compiler%'),
      "ccache_cmake":
      '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DCMAKE_C_COMPILER_LAUNCHER=ccache'
  })

  jobs = {}
  jobs.update(ubuntu())
  jobs.update(mac())

  workflow = Workflow(name='default', on=on, env=env, jobs=jobs)
  print(yaml.dump(resolve(workflow), sort_keys=False, width=1024))
