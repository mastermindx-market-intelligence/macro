"""Native visual readback for the retained comparison candidate."""
import os
from pathlib import Path
import pytest
from test_crypto_intelligence_r4_browser import comparison_page, browser, page_url, _capture

@pytest.mark.parametrize("lang,width,touch", [("en",390,False),("zh",320,True)])
def test_comparison_visual_readback(comparison_page,lang,width,touch):
    page,_=comparison_page(lang,width,touch=touch)
    out=Path(os.environ["MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR"]);out.mkdir(parents=True,exist_ok=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.locator('[data-view="markets"]').screenshot(path=str(out/f"comparison-markets-{lang}-{width}.png"))
    page.locator('[data-asset-row="ETH"] .cri-asset').click()
    _capture(page,f"comparison-asset-{lang}-{width}")
    page.locator("#cri-dialog-body [data-comparison-basis] summary").click()
    _capture(page,f"comparison-basis-{lang}-{width}")
    variant="missing" if lang=="en" else "empty"
    absent,_=comparison_page(lang,width,variant,touch=touch)
    assert not absent.locator("#cri-reset").is_visible()
    absent.locator('[data-view="markets"]').screenshot(path=str(out/f"comparison-{variant}-{lang}-{width}.png"))
