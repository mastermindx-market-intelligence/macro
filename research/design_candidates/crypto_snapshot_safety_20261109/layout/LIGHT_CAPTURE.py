from pathlib import Path
import os
import pytest
import test_crypto_intelligence_r4_browser as cases
from test_crypto_intelligence_r4_browser import browser, page_url, snapshot_page


@pytest.mark.parametrize("lang,width", [("en",390),("zh",320)])
def test_saved_layout_light_capture(snapshot_page,lang,width):
    page=snapshot_page(lang,width,start="#scenarios?h=7")
    page.locator("html").evaluate("node => node.dataset.theme='light'")
    target=cases._layout_frozen(page)
    cases._seed(page,[target])
    cases._open_saved_from_list(page,target,lang)
    assert page.locator("#cri-dialog-body").get_by_text(target["condition_"+lang],exact=True).is_visible()
    assert page.locator('[data-drawer-focus="review"]').evaluate("node=>node.getBoundingClientRect().bottom<=innerHeight")
    cases._capture(page,f"layout-saved-{lang}-{width}-light")
