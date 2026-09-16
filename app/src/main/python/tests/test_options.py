"""helper.start() and helper.unnew() translate app state into FanFicFare CLI
options. These tests stop FanFicFare at the door and inspect what it was given."""
from unittest import mock

import pytest

import helper
from helper import Handler


@pytest.fixture
def cli_main(clean_helper_state):
    with mock.patch.object(helper.fanficfare.cli, 'main') as m:
        yield m


def _options(cli_main):
    args, kwargs = cli_main.call_args
    return args[0], kwargs


def test_default_is_epub_update(cli_main):
    helper.start(Handler('u'), 'https://example.com/s')
    opts, kwargs = _options(cli_main)
    assert opts[-1] == 'https://example.com/s'
    assert '--update-epub' in opts and '--non-interactive' in opts and '--progressbar' in opts
    assert '-U' not in opts and '--force' not in opts and '--save-cache' not in opts
    assert kwargs['passed_defaultsini'] == helper.default_ini


def test_force_download_uses_U_and_force(cli_main):
    helper.start(Handler('u'), 'https://example.com/s', forceDownload=True)
    opts, _ = _options(cli_main)
    assert '-U' in opts and '--force' in opts and '--update-epub' not in opts


def test_save_cache_flag(cli_main):
    helper.start(Handler('u'), 'https://example.com/s', save_cache=True)
    opts, _ = _options(cli_main)
    assert '--save-cache' in opts


def test_epub_filename_argument_passes_through(cli_main):
    """For updates Kotlin passes the existing EPUB's name instead of a URL."""
    helper.start(Handler('u'), 'Some Story-ao3_1.epub')
    opts, _ = _options(cli_main)
    assert opts[-1] == 'Some Story-ao3_1.epub'


def test_start_patches_get_adapter_and_registers_handler(cli_main):
    h = Handler('u')
    helper.start(h, 'https://example.com/s')
    assert helper.fanficfare.cli.adapters.getAdapter is helper.my_get_adapter
    assert helper.get_handler() is h


def test_start_without_handler_creates_stub(cli_main):
    helper.start(None, 'https://example.com/s')
    assert isinstance(helper.get_handler(), Handler)


def test_success_and_failure_reach_finish(cli_main):
    h = Handler('u')
    helper.start(h, 'https://example.com/s')
    assert h.is_finished

    h2 = Handler('u')
    cli_main.side_effect = RuntimeError('site exploded')
    helper.start(h2, 'https://example.com/s')
    assert h2.is_finished
    assert 'site exploded' in h2.output


def test_personal_ini_is_read_and_forwarded(cli_main, tmp_path):
    ini = tmp_path / 'personal.ini'
    ini.write_text('[defaults]\nis_adult: true\n')
    old = helper.personal_ini
    try:
        helper.read_personal_ini(str(ini))
        helper.start(Handler('u'), 'https://example.com/s')
        _, kwargs = _options(cli_main)
        assert 'is_adult: true' in kwargs['passed_personalini']
    finally:
        helper.personal_ini = old


def test_unnew_options(cli_main):
    helper.unnew('/tmp/x.epub')
    opts, kwargs = _options(cli_main)
    assert opts == ['--unnew', '/tmp/x.epub']
    assert kwargs['passed_defaultsini'] == helper.default_ini


# --- include_images -----------------------------------------------------------
# FanFicFare's --update-epub sets never_make_cover unless --update-cover is
# also given, so the flag must accompany any non-"false" setting.

@pytest.mark.parametrize('value', ['coveronly', 'true'])
def test_images_enabled_adds_update_cover(cli_main, value):
    helper.start(Handler('u'), 'https://example.com/s', include_images=value)
    opts, kwargs = _options(cli_main)
    assert '--update-cover' in opts
    assert 'include_images: %s' % value in kwargs['passed_personalini']


def test_images_disabled_is_the_default(cli_main):
    helper.start(Handler('u'), 'https://example.com/s')
    opts, kwargs = _options(cli_main)
    assert '--update-cover' not in opts
    assert 'include_images: false' in kwargs['passed_personalini']


def test_app_setting_precedes_personal_ini(cli_main, tmp_path):
    """The app's value is written first so the user's personal.ini still wins."""
    ini = tmp_path / 'personal.ini'
    ini.write_text('[defaults]\ninclude_images: true\n')
    old = helper.personal_ini
    try:
        helper.read_personal_ini(str(ini))
        helper.start(Handler('u'), 'https://example.com/s', include_images='false')
        _, kwargs = _options(cli_main)
        text = kwargs['passed_personalini']
        assert text.index('include_images: false') < text.index('include_images: true')
    finally:
        helper.personal_ini = old
