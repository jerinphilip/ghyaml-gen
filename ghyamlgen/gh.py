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


class Job(YAMLRenderable):

  def __init__(
      self,
      name,
      runs_on,
      env=None,
      outputs=None,
      condition=None,
      steps=None,
  ):

    self.fields = {
        "name": name,
        "env": env,
        "runs-on": runs_on,
        "if": condition,
        "needs": None,
        "steps": steps,
        "outputs": outputs,
    }

  def name(self):
    return self.fields["name"]

  def needs(self, job, OpExpr):
    condition = "{}".format(OpExpr(job))
    fields = {
        "if": condition,
        "needs": job.fields["name"],
    }

    self.fields.update(fields)


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

    keys = [
        GitHubExpr('github.job'),
        GitHubExpr('steps.ccache_vars.outputs.hash'),
        GitHubExpr('github.ref'),
        GitHubExpr('steps.ccache_vars.outputs.timestamp')
    ]

    transform = lambda keys: '-'.join(['ccache'] + keys)

    self.fields = {
        "name": "Cache-op for build-cache through ccache",
        "uses": "actions/cache@v2",
        "with": {
            "path":
                GitHubExpr('env.ccache_dir'),
            "key":
                transform(keys),
            "restore-keys":
                Snippet('\n'.join(
                    [transform(keys[:-i]) for i in range(len(keys))]))
        }
    }


class UploadArtifacts(YAMLRenderable):

  def __init__(self):
    self.fields = {
        "name": "Upload regression-tests artifacts",
        "uses": "actions/upload-artifact@v2",
        "if": GitHubExpr("always()"),
        "with": {
            "name":
                "brt-{}".format(GitHubExpr("github.job")),
            "path":
                Snippet('\n'.join([
                    "bergamot-translator-tests/**/*.expected",
                    "bergamot-translator-tests/**/*.log",
                    "bergamot-translator-tests/**/*.out",
                ])),
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
                     run="MARIAN=../build ./run_brt.sh ${{ env.brt_tags }}"),
        UploadArtifacts()
    ])


class ImportedSnippet(JobShellStep):

  def __init__(self, name, fpath, working_directory=None):
    contents = None
    with open(fpath) as fp:
      contents = fp.read().strip()
    super().__init__(name=name,
                     run=contents,
                     working_directory=working_directory)


class HardFailBash(JobShellStep):

  def __init__(self):
    super().__init__(name="Hard fail to check trigger for other workflow",
                     run='exit 1',
                     shell='bash')


class LogContext(YAMLRenderable):

  def __init__(self, context):
    self.fields = {
        "name": "Dump {} context".format(context),
        "env": {
            "{}_CONTEXT".format(context.upper()):
                GitHubExpr('toJSON({})'.format(context))
        },
        "run": "echo ${}_CONTEXT".format(context.upper())
    }


class Evaluate(YAMLRenderable):

  def __init__(self, expr):
    self.fields = {
        "name": "Evaluate {}".format(expr),
        "env": {
            "EXPR_VALUE": GitHubExpr(expr)
        },
        "run": "echo $EXPR_VALUE"
    }
