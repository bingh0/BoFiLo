"""
Test suite for helper.py, the Python side of the Kotlin <-> FanFicFare bridge.

Run from the repository root:

    .venv/bin/python -m pytest app/src/main/python/tests

No network access is needed. The end-to-end tests replay AO3 story 2080878
("I Am Groot") from a pickled FanFicFare BasicCache in fixtures/, serving it
through the same web_request hook the Android app uses for GeckoView.
"""
import os
import pickle
import sys
import threading

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..'))

import helper  # noqa: E402  (needs sys.path above)

STORY_URL = 'https://archiveofourown.org/works/2080878'
CACHE_FILE = os.path.join(HERE, 'fixtures', 'ao3_2080878_cache.pickle')


@pytest.fixture(scope='session')
def fixture_cache():
    with open(CACHE_FILE, 'rb') as f:
        return pickle.load(f)


class FixtureHandler(helper.Handler):
    """A Handler whose web_request answers from the pickled cache, standing in
    for the Kotlin StoryDownloadHelper + GeckoView."""

    def __init__(self, url, cache, adult=False):
        super().__init__(url)
        self.cache = cache
        self.adult = adult
        self.web_calls = []
        self.started_with = None
        self.finished_with = None

    def web_request(self, method, url, kargs=None):
        self.web_calls.append((method, url))
        if url not in self.cache:
            raise KeyError('not in fixture: %s' % url)
        data = self.cache[url][0]
        return data.decode('utf-8') if isinstance(data, bytes) else data

    def is_adult(self):
        return self.adult

    def start(self, url):
        self.started_with = url

    def finish(self, success):
        super().finish(success)
        self.finished_with = success


@pytest.fixture
def make_handler(fixture_cache):
    def _make(url=STORY_URL, **kw):
        return FixtureHandler(url, fixture_cache, **kw)
    return _make


@pytest.hookimpl(wrapper=True, trylast=True)
def pytest_runtest_call(item):
    """helper.py wraps sys.stdout/stderr at import so FanFicFare's output reaches
    the registered handler. pytest reinstalls its own streams right before each
    test body runs, so re-wrap them the same way, inside pytest's capture."""
    out, err = sys.stdout, sys.stderr
    sys.stdout = helper.MyStdOut(out)
    sys.stderr = helper.MyStdOut(err, "\nError: ")
    try:
        return (yield)
    finally:
        sys.stdout, sys.stderr = out, err


@pytest.fixture
def clean_helper_state():
    """helper.start() registers a per-thread handler and patches FanFicFare's
    getAdapter for the life of the process. Undo both after each test."""
    yield
    helper.handlers.pop(threading.get_ident(), None)
    helper.fanficfare.cli.adapters.getAdapter = helper.originalGetAdapter


@pytest.fixture
def in_tmp(tmp_path, clean_helper_state):
    """FanFicFare writes the EPUB into the current directory."""
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(old)
