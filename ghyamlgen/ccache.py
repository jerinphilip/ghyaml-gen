from .gh import JobShellStep


class CcacheEnv(JobShellStep):

  def __init__(self, config):
    env = {
        'COMPILER_CHECK': config["compilercheck"],
        'BASE_DIR': config["base_dir"],
        'COMPRESS': config["compress"],
        'DIR': config["dir"],
        'MAXSIZE': config["maxsize"]
    }

    commands = [
        'echo "CCACHE_{key}={value}" >> $GITHUB_ENV'.format(
            key=key, value=value) for key, value in env.items()
    ]

    run = '\n'.join(commands)
    super().__init__(name="ccache environment setup", run=run)


class CcacheVars(JobShellStep):

  def __init__(self, check, cmd=False):
    # check can be string value or command, so
    safeCheck = "{echo} {check}".format(echo='' if cmd else 'echo', check=check)
    ccache_vars = {"hash": safeCheck, "timestamp": "date '+%Y-%m-%dT%H.%M.%S'"}
    commands = [
        'echo "::set-output name={key}::$({evalExpr})"'.format(
            key=key, evalExpr=evalExpr)
        for key, evalExpr in ccache_vars.items()
    ]

    super().__init__(
        name="Generate ccache_vars for ccache based on machine",
        run='\n'.join(commands),
        id="ccache_vars",
        shell="bash")


class CCacheProlog(JobShellStep):

  def __init__(self):
    commands = [
        'ccache -s # Print current cache stats',
        'ccache -z # Zero cache entry',
    ]
    super().__init__(name="ccache prolog", run='\n'.join(commands))


class CCacheEpilog(JobShellStep):

  def __init__(self):
    commands = [
        'ccache -s # Print current cache stats',
    ]
    super().__init__(name="ccache epilog", run='\n'.join(commands))
