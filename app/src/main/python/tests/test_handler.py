"""The Handler stub must mirror what Kotlin's StoryDownloadHelper exposes
through Chaquopy, because helper.py calls these on the Kotlin object."""
import threading

import helper
from helper import Handler


def test_stub_records_callbacks():
    h = Handler('https://example.com/s')
    h.title('A Title')
    h.filename('a.epub')
    h.chapters(2, 5)
    h.add_output('x')
    h.finish(True)
    assert (h._title, h._filename, h.chapters_now, h.chapters_max) == ('A Title', 'a.epub', 2, 5)
    assert h.output == 'x' and h.is_finished


def test_web_request_takes_kargs_positionally():
    """MyFetcher calls handler.web_request(method, url, kargs) with kargs as a
    plain dict, which is how the Kotlin signature looks."""
    h = Handler('https://example.com/s')
    try:
        h.web_request('GET', 'https://example.com/s', {'headers': {}})
    except NotImplementedError:
        pass  # the stub cannot fetch, but it must accept the call shape
    else:
        raise AssertionError('stub web_request should raise NotImplementedError')


def test_stub_get_login_refuses():
    h = Handler('https://example.com/s')
    try:
        h.get_login(True)
    except ValueError:
        pass
    else:
        raise AssertionError('stub get_login should raise ValueError')


def test_stdout_is_routed_to_registered_handler(clean_helper_state):
    h = Handler('https://example.com/s')
    helper.handlers[threading.get_ident()] = h
    print('hello from python')
    assert 'hello from python' in h.output


def test_stderr_gets_error_prefix(clean_helper_state):
    import sys
    h = Handler('https://example.com/s')
    helper.handlers[threading.get_ident()] = h
    print('boom', file=sys.stderr)
    assert 'Error: boom' in h.output


def test_handlers_are_per_thread(clean_helper_state):
    h = Handler('https://example.com/s')
    helper.handlers[threading.get_ident()] = h
    seen = []
    t = threading.Thread(target=lambda: seen.append(helper.get_handler()))
    t.start(); t.join()
    assert helper.get_handler() is h
    assert seen == [None]
