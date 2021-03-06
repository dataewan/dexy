from dexy.exceptions import UserFeedback
from dexy.filters.git import repo_from_path
from dexy.filters.git import repo_from_url
from dexy.filters.git import generate_commit_info
from dexy.tests.utils import assert_in_output
from dexy.tests.utils import runfilter
from dexy.tests.utils import tempdir
from nose.exc import SkipTest
import os
import json

REMOTE_REPO_HTTPS = "https://github.com/ananelson/dexy-templates"
PATH_TO_LOCAL_REPO = os.path.expanduser("~/dev/testrepo")
# TODO use subprocess to check out a repo to a temp dir, or have a repo in data
# dir, or use [gasp] submodules.

try:
    import pygit2
    SKIP = not os.path.exists(PATH_TO_LOCAL_REPO)
except ImportError:
    SKIP = True

def skip():
    if SKIP:
        raise SkipTest("The pygit2 package was not found.")

def test_run_gitrepo():
    with runfilter("repo", REMOTE_REPO_HTTPS) as doc:
        assert len(doc.wrapper.nodes) > 20

def test_generate_commit_info():
    skip()
    repo, remote = repo_from_url(REMOTE_REPO_HTTPS)

    refs = repo.listall_references()
    ref = repo.lookup_reference(refs[0])
    commit = repo[ref.oid]
    commit_info = generate_commit_info(commit)

    assert commit_info['author-name'] == "Ana Nelson"
    assert commit_info['author-email'] == "ana@ananelson.com"

def test_git_commit():
    with runfilter("gitcommit", REMOTE_REPO_HTTPS) as doc:
        output = doc.output_data()
        patches = json.loads(output['patches'])
        assert output['author-name'] == "Ana Nelson"
        assert output['author-email'] == "ana@ananelson.com"
        #assert output['message'] == "Add README file."
        #assert output['hex'] == "2f15837e64a70e4d34b924f6f8c371a266d16845"

def test_git_log():
    assert_in_output("gitlog", PATH_TO_LOCAL_REPO,
            "Add README file.")

def test_git_log_remote():
    assert_in_output("gitlog", REMOTE_REPO_HTTPS,
            "Rename")

def test_repo_from_url():
    skip()
    repo, remote = repo_from_url(REMOTE_REPO_HTTPS)
    assert remote.name == 'origin'
    assert remote.url == REMOTE_REPO_HTTPS

def test_repo_from_path():
    skip()
    repo, remote = repo_from_path(PATH_TO_LOCAL_REPO)
    assert ".git" in repo.path
    assert isinstance(repo.head, pygit2.Commit)
    assert "README" in repo.head.message

def test_repo_from_invalid_path():
    skip()
    with tempdir():
        try:
            repo, remote = repo_from_path(".")
            assert False
        except UserFeedback as e:
            assert "no git repository was found at '.'" in str(e)

def test_run_git():
    with runfilter("git", PATH_TO_LOCAL_REPO) as doc:
        doc.output_data()

def test_run_git_remote():
    with runfilter("git", REMOTE_REPO_HTTPS) as doc:
        doc.output_data()
