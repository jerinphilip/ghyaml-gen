from . import YAMLRenderable, Snippet, GitHubExpr


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
    condition = "needs.{jobname}.result {suffix}".format(
        jobname=job.fields["name"], suffix=suffix)
    self.fields = {"needs": job.fields["needs"], "if": GitHubExpr(condition)}


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


class GHCache(YAMLRenderable):
  def __init__(self):
    self.fields = {
        "name": "Cache-op for build-cache through ccache",
        "uses": "actions/cache@v2",
        "with": {
            "path":
                '${{ env.CCACHE_DIR }}',
            "key":
                "ccache-${{ matrix.name }}-${{ steps.ccache_vars.outputs.hash }}-${{ github.ref }}-${{ steps.ccache_vars.outputs.timestamp }}",
            "restore-keys":
                Snippet('\n'.join([
                    "ccache-${{ matrix.name }}-${{ steps.ccache_vars.outputs.hash }}-${{ github.ref }}-",
                    "ccache-${{ matrix.name }}-${{ steps.ccache_vars.outputs.hash }}-",
                    "ccache-${{ matrix.name }}-",
                ]))
        }
    }


class BRT(list):

  def __init__(self, working_directory='bergamot-translator-tests'):
    super().__init__([
        JobShellStep(name="Install regression-test framework (BRT)",
                     working_directory=working_directory,
                     run="make install"),
        JobShellStep(name="Run regression-tests (BRT)",
                     working_directory=working_directory,
                     run="MARIAN=../build ./run_brt.sh ${{ env.brt_tags }}")
    ])


class ImportedSnippet(JobShellStep):

  def __init__(self, name, fpath, working_directory=None):
    contents = None
    with open(fpath) as fp:
      contents = fp.read().strip()
    super().__init__(name=name,
                     run=contents,
                     working_directory=working_directory)
