import sublime_plugin
import os.path
import re
import sublime


class VcsSiteLinkCommand(sublime_plugin.TextCommand):

    def row(self, position):
        return self.view.rowcol(position)[0] + 1

    def run(self, edit):
        filename = self.view.file_name()  
        selection = self.view.sel()

        if not filename:
            return

        if not len(selection):
            return 

        region = self.view.sel()[0]
        b = self.row(region.begin())
        e = self.row(region.end())
        vcs_site = self.guess_vcs_site(filename)

        if not vcs_site:
            return

        sublime.set_clipboard(vcs_site.link(filename, (b, e)))

    def guess_vcs_site(self, filename):

        def find_remote_origin(config):
            for section, properties in config:
                if section == 'remote "origin"':
                    props = dict(properties)
                    return props

        git_dir = self.find_git_dir(filename)
        if not git_dir:
            return

        head_ref = open(os.path.join(git_dir, '.git', 'HEAD')).read().strip()[5:]
        commit_id = open(os.path.join(git_dir, '.git', head_ref)).read().strip()
        
        config = parse_git_config(os.path.join(git_dir, '.git', 'config'))
        ro_props = find_remote_origin(config)


        git_url = ro_props['url']
        if 'bitbucket' in git_url:
            project_path = git_url.split(':')[1]
            return BitbucketSite(git_dir, project_path, commit_id)
        elif 'github.com' in git_url:
            project_path = git_url.split(':')[1]
            return GithubSite(git_dir, project_path, commit_id)
        else:
            return

    def find_git_dir(self, filename):
        path = filename
        while(path):
            path = os.path.dirname(path)
            if '.git' in os.listdir(path):
                return path

 



class BitbucketSite:
    path_tpl = 'https://bitbucket.org/{}/src/{}/{}#Line-{}:{}'

    def __init__(self, git_dir, project_path, commit_id):
        self.git_dir = git_dir
        self.project_path = project_path
        self.commit_id = commit_id
        

    def link(self, filename, lines):
        b, e = lines
        file_path = os.path.relpath(filename, start=self.git_dir)
        return self.path_tpl.format(self.project_path, self.commit_id, file_path, b, e)

class GithubSite:
    path_tpl = 'https://github.com/{}/blob/{}/{}#L{}-L{}'

    def __init__(self, git_dir, project_path, commit_id):
        self.git_dir = git_dir
        self.project_path = project_path[:-4] if project_path.endswith(".git") else project_path
        self.commit_id = commit_id

    def link(self, filename, lines):
        b, e = lines
        file_path = os.path.relpath(filename, start=self.git_dir)
        return self.path_tpl.format(self.project_path, self.commit_id, file_path, b, e)

# Hacky config parser
def parse_git_config(filename):
    section_re = re.compile(r"\[([^]]*)\]")
    property_re = re.compile(r"\s*([^=]+)=(.*)")
    lines = open(filename).readlines()
    def g():
        it = iter(lines)

        while True:
            l = next(it).strip()
            m = section_re.match(l)
            if m:
                section = m.group(1)
                break

        section_properties = []
        while True:
            l = next(it).strip()
            if property_re.match(l):
                m = property_re.match(l)
                section_properties.append((m.group(1).strip(), m.group(2).strip()))
            elif section_re.match(l):
                yield (section, section_properties)
                section = section_re.match(l).group(1)
                section_properties = []

        yield (section, section_properties)
    return list(g())
