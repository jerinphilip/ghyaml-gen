import sys
import os

basedir = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(basedir, "../../")
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
                      "examples/bergamot-translator/native-ubuntu/20-build.sh",
                      working_directory="build"),
  ]

  def ccache(build):
    return [
        CcacheVars(check=GitHubExpr('env.cache_cmd')),
        GHCache(),
        CcacheEnv(check=GitHubExpr('env.cache_cmd'),
                  base_dir=GitHubExpr('github.workspace'),
                  directory=os.path.join(GitHubExpr('github.workspace'),
                                         '.ccache'),
                  compress="true",
                  maxsize="100M"),
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

  def build_env(with_cache=False):
      maybeCcache = '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DCMAKE_C_COMPILER_LAUNCHER=ccache' if with_cache else ''
      env = {
          "gcc":
              8,
          "CCACHE_DIR":
              QuotedExpr(os.path.join(GitHubExpr('github.workspace'), '.ccache')),
          "cache_cmd":
              QuotedExpr(
                  'bash ${GITHUB_WORKSPACE}/scripts/ci/compiler-hash.sh %compiler%'
              ),
          "cmake":
              QuotedExpr(
                  '-DCMAKE_BUILD_TYPE=Release -DCOMPILE_TESTS=on {maybeCcache}'.format(maybeCcache=maybeCcache)
              ),
          # "brt_tags": QuotedExpr("'#native'"),
          "brt_tags":
              None,
      }
      return env

  cached = Job(name='cached',
               env=build_env(with_cache=True),
               runs_on='ubuntu-18.04',
               steps=merge(setup, ccache(build), build_epilog, BRT()))

  fresh = Job(name='fresh',
              env=build_env(with_cache=False),
              needs=Needs(job=cached, result='failure'),
              runs_on='ubuntu-18.04',
              steps=merge(setup, build, build_epilog, BRT()))

  jobs = {"cached": cached, "fresh": fresh}
  workflow = Workflow(name='default', on=on, env=None, jobs=jobs)
  print(yaml.dump(resolve(workflow), sort_keys=False, width=1024))
