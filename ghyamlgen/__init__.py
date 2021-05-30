import yaml

from .yml import GitHubExpr, Snippet, QuotedExpr, GitHubMapping

yaml.add_representer(Snippet, Snippet.representer)
yaml.add_representer(GitHubExpr, GitHubExpr.representer)
yaml.add_representer(QuotedExpr, QuotedExpr.representer)
yaml.add_representer(GitHubMapping, GitHubMapping.representer)


class YAMLRenderable:
  pass


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


from .gh import *
from .ccache import *
