"""Flattened tools.* imports alias tools.tools.* modules."""

from tools.ohlcv import fetch_ohlcv

from tools.tools.ohlcv import fetch_ohlcv as fetch_ohlcv_nested


def test_flat_ohlcv_import_aliases_nested_module():
    assert fetch_ohlcv is fetch_ohlcv_nested


def test_flat_imports_cover_all_wrappers():
    import tools.avgpe as flat_avgpe
    import tools.fundamentals as flat_fundamentals
    import tools.global_news as flat_global_news
    import tools.indicators as flat_indicators
    import tools.insider as flat_insider
    import tools.macro as flat_macro
    import tools.news as flat_news
    import tools.ohlcv as flat_ohlcv
    import tools.statement as flat_statement
    import tools.vwap as flat_vwap

    import tools.tools.avgpe as nested_avgpe
    import tools.tools.fundamentals as nested_fundamentals
    import tools.tools.global_news as nested_global_news
    import tools.tools.indicators as nested_indicators
    import tools.tools.insider as nested_insider
    import tools.tools.macro as nested_macro
    import tools.tools.news as nested_news
    import tools.tools.ohlcv as nested_ohlcv
    import tools.tools.statement as nested_statement
    import tools.tools.vwap as nested_vwap

    assert flat_avgpe is nested_avgpe
    assert flat_fundamentals is nested_fundamentals
    assert flat_global_news is nested_global_news
    assert flat_indicators is nested_indicators
    assert flat_insider is nested_insider
    assert flat_macro is nested_macro
    assert flat_news is nested_news
    assert flat_ohlcv is nested_ohlcv
    assert flat_statement is nested_statement
    assert flat_vwap is nested_vwap
