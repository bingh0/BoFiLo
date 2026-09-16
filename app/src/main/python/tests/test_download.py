"""End-to-end: helper.start() drives FanFicFare through the same hooks the app
uses, with AO3 pages replayed from the fixture through web_request."""
import os
import zipfile

import helper
from tests.conftest import STORY_URL


def _epubs(path):
    return sorted(f for f in os.listdir(path) if f.endswith('.epub'))


def _run(handler, in_tmp, **kw):
    helper.start(handler, handler.url, **kw)
    return _epubs(in_tmp)


def test_download_via_gecko_hook_produces_epub(make_handler, in_tmp):
    h = make_handler()
    epubs = _run(h, in_tmp)
    assert h.finished_with is True, h.output
    assert epubs == ['I Am Groot-ao3_2080878.epub']
    with zipfile.ZipFile(in_tmp / epubs[0]) as z:
        names = z.namelist()
        assert 'mimetype' in names and 'content.opf' in names
        assert any(n.endswith('.xhtml') for n in names)


def test_all_requests_went_through_the_handler(make_handler, in_tmp):
    h = make_handler()
    _run(h, in_tmp)
    urls = [u for _, u in h.web_calls]
    assert STORY_URL in urls and len(urls) == 3
    assert all(u.startswith('https://archiveofourown.org/') for u in urls)


def test_progress_callbacks(make_handler, in_tmp):
    h = make_handler()
    _run(h, in_tmp)
    assert h.started_with == STORY_URL
    assert h._title == 'I Am Groot'
    assert h._filename == 'I Am Groot-ao3_2080878.epub'
    assert (h.chapters_now, h.chapters_max) == (1, 1)


def test_second_run_updates_existing_epub(make_handler, in_tmp):
    first = _run(make_handler(), in_tmp)
    h = make_handler()
    second = _run(h, in_tmp)
    assert h.finished_with is True, h.output
    assert first == second
    assert 'Failed to read epub for update' not in h.output
    assert 'Updating' in h.output


def test_force_redownload(make_handler, in_tmp):
    _run(make_handler(), in_tmp)
    h = make_handler()
    epubs = _run(h, in_tmp, forceDownload=True)
    assert h.finished_with is True, h.output
    assert epubs == ['I Am Groot-ao3_2080878.epub']


def test_missing_page_fails_cleanly(make_handler, in_tmp, fixture_cache):
    partial = {k: v for k, v in fixture_cache.items() if not k.endswith('/navigate')}
    h = make_handler()
    h.cache = partial
    _run(h, in_tmp)
    assert h.finished_with is False
    assert 'not in fixture' in h.output
    assert _epubs(in_tmp) == []


def test_unnew_rewrites_epub_in_place(make_handler, in_tmp):
    epub = in_tmp / _run(make_handler(), in_tmp)[0]
    before = epub.stat().st_mtime_ns
    helper.unnew(str(epub))
    with zipfile.ZipFile(epub) as z:
        assert z.testzip() is None
        assert 'content.opf' in z.namelist()
    assert epub.stat().st_mtime_ns >= before
