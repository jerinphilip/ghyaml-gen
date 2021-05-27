class Snippet(str):

  @staticmethod
  def representer(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
      return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


class GitHubExpr(str):

  def __new__(cls, value):
    value = '${{ ' + value + ' }}'
    return str.__new__(cls, value)

  @staticmethod
  def representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)
