"""MyStory, MyAdapter and MyFetcher wrap FanFicFare objects to surface progress
and to route prompts and web requests to the Kotlin handler."""
import threading
from unittest import mock

import pytest

import helper
from fanficfare import exceptions
from helper import Handler, MyAdapter, MyFetcher, MyStory


class Recorder(Handler):
    def __init__(self):
        super().__init__('u')
        self.events = []
        self.login_answers = []
        self.adult = False

    def chapters(self, now, max_):
        self.events.append(('chapters', now, max_))

    def title(self, v):
        self.events.append(('title', v))

    def filename(self, v):
        self.events.append(('filename', v))

    def get_login(self, password_only=False):
        self.events.append(('get_login', password_only))
        return self.login_answers.pop(0)

    def is_adult(self):
        return self.adult

    def start(self, url):
        self.events.append(('start', url))

    def web_request(self, method, url, kargs=None):
        self.events.append(('web', method, url))
        return '<html>served by handler</html>'


@pytest.fixture
def rec(clean_helper_state):
    r = Recorder()
    helper.handlers[threading.get_ident()] = r
    return r


class FakeStory:
    def __init__(self):
        self.chapters = []
        self.meta = {}
        self.count = 3

    def getChapterCount(self):
        return self.count

    def addChapter(self, chap, newchap=False, **kw):
        self.chapters.append(chap)

    def setMetadata(self, key, value, condremoveentities=True, **kw):
        self.meta[key] = value

    def formatFileName(self, template, allowunsafefilename=True, **kw):
        return 'Formatted-%s.epub' % template


def test_story_progress_and_title(rec):
    s = MyStory(FakeStory())
    s.setMetadata('numChapters', 3)
    s.setMetadata('title', 'T', True)
    s.addChapter({'title': 'c1'})
    s.addChapter({'title': 'c2'}, newchap=True)
    assert s.formatFileName('${title}', allowunsafefilename=False) == 'Formatted-${title}.epub'
    assert rec.events == [('chapters', 0, 3), ('title', 'T'), ('chapters', 1, 3), ('chapters', 2, 3),
                          ('filename', 'Formatted-${title}.epub')]


def test_story_wrapper_is_transparent(rec):
    inner = FakeStory()
    s = MyStory(inner)
    s.count = 9                      # attribute writes land on the wrapped story
    assert inner.count == 9
    assert s.getChapterCount() == 9  # attribute reads are forwarded
    assert s.story is inner


class FakeAdapter:
    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = 0
        self.is_adult = False
        self.username = self.password = None

    def getStoryMetadataOnly(self, get_cover=True, **kw):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return 'metadata'


def test_adapter_retries_after_password_prompt(rec):
    rec.login_answers = [['pw', None]]
    a = MyAdapter(FakeAdapter([exceptions.FailedToLogin('u', None, passwdonly=True)]))
    assert a.getStoryMetadataOnly() == 'metadata'
    assert ('get_login', True) in rec.events
    assert a.adapter.password == 'pw' and a.adapter.calls == 2


def test_adapter_retries_after_username_password_prompt(rec):
    rec.login_answers = [['pw', 'user']]
    a = MyAdapter(FakeAdapter([exceptions.FailedToLogin('u', 'user')]))
    assert a.getStoryMetadataOnly(get_cover=False) == 'metadata'
    assert ('get_login', False) in rec.events
    assert (a.adapter.username, a.adapter.password) == ('user', 'pw')


def test_adapter_gives_up_after_second_login_failure(rec):
    """Two attempts, each asking Kotlin for credentials; then the wrapper
    silently returns None (existing behaviour, documented here)."""
    rec.login_answers = [['pw', 'user'], ['pw2', 'user2']]
    a = MyAdapter(FakeAdapter([exceptions.FailedToLogin('u', 'user'), exceptions.FailedToLogin('u', 'user')]))
    assert a.getStoryMetadataOnly() is None
    assert a.adapter.calls == 2
    assert [e for e in rec.events if e[0] == 'get_login'] == [('get_login', False)] * 2


def test_adult_check_passes_when_user_allows(rec):
    rec.adult = True
    a = MyAdapter(FakeAdapter([exceptions.AdultCheckRequired('u')]))
    assert a.getStoryMetadataOnly() == 'metadata'
    assert a.adapter.is_adult is True


def test_adult_check_propagates_when_user_forbids(rec):
    rec.adult = False
    a = MyAdapter(FakeAdapter([exceptions.AdultCheckRequired('u')]))
    with pytest.raises(exceptions.AdultCheckRequired):
        a.getStoryMetadataOnly()


def test_login_failure_propagates_without_handler(clean_helper_state):
    a = MyAdapter(FakeAdapter([exceptions.FailedToLogin('u', 'user')]))
    with pytest.raises(exceptions.FailedToLogin):
        a.getStoryMetadataOnly()


def _fetcher():
    return MyFetcher(lambda *a, **k: None, lambda *a, **k: [])


@pytest.mark.parametrize('url', ['https://archiveofourown.org/works/1',
                                 'https://www.fanfiction.net/s/1/1/x'])
def test_fetcher_routes_ao3_and_ffnet_to_handler(rec, url):
    resp = _fetcher().request('GET', url, headers={})
    assert resp.content == '<html>served by handler</html>'
    assert ('web', 'GET', url) in rec.events


def test_fetcher_leaves_other_sites_to_requests(rec):
    with mock.patch.object(helper.fanficfare.fetchers.fetcher_requests.RequestsFetcher, 'request',
                           return_value='native') as native:
        assert _fetcher().request('GET', 'https://www.royalroad.com/fiction/1') == 'native'
    native.assert_called_once()
    assert not [e for e in rec.events if e[0] == 'web']


def test_get_adapter_injects_fetcher_only_for_gecko_sites(rec):
    class Config:
        fetcher = None
        getConfig = staticmethod(lambda *a, **k: None)
        getConfigList = staticmethod(lambda *a, **k: [])

    class Adapter:
        def __init__(self, domain):
            self.domain, self.url, self.story = domain, 'https://%s/x' % domain, FakeStory()

        def getSiteDomain(self):
            return self.domain

    for domain, injected in [('archiveofourown.org', True), ('www.royalroad.com', False)]:
        cfg = Config()
        with mock.patch.object(helper, 'originalGetAdapter', return_value=Adapter(domain)):
            wrapped = helper.my_get_adapter(cfg, 'https://%s/x' % domain)
        assert isinstance(wrapped, MyAdapter) and isinstance(wrapped.story, MyStory)
        assert isinstance(cfg.fetcher, MyFetcher) == injected
        assert ('start', wrapped.url) in rec.events
