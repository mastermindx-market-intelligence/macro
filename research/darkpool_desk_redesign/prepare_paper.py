"""Prepare editable Paper HTML for the observed browser layouts without writing to Paper."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

CAPTURE = r"""() => {
  const esc = value => String(value).replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[c]);
  const px = n => Math.round(n * 100) / 100 + 'px';
  const spec = ['background-color','color','border-top','border-right','border-bottom','border-left',
      'border-radius','font-family','font-size','font-weight','font-style','line-height',
      'letter-spacing','text-transform','text-align','opacity'];
  function render(el, parent) {
    const box = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (cs.display==='none' || box.width < 2 || box.height < 2 ||
        el.matches('script, style, .sr, .jump, #announce') ||
        (el.closest('details:not([open])') && !el.matches('details,summary'))) return '';
    const bounds = 'position:absolute;box-sizing:border-box;left:'+px(box.x-parent.x)+
      ';top:'+px(box.y-parent.y)+';width:'+px(box.width)+';height:'+px(box.height)+';';
    if (el.tagName.toLowerCase()==='svg') {
      const clone = el.cloneNode(true);
      const nodes = [el,...el.querySelectorAll('*')];
      [clone,...clone.querySelectorAll('*')].forEach((node,i) => {
        const cn = getComputedStyle(nodes[i]);
        for (const prop of ['fill','stroke','stroke-width','stroke-dasharray','font-size','font-family','font-weight','paint-order']) {
          node.style.setProperty(prop,cn.getPropertyValue(prop));
        }
        node.removeAttribute('tabindex'); node.removeAttribute('class'); node.removeAttribute('role');
      });
      clone.setAttribute('width',box.width); clone.setAttribute('height',box.height);
      return '<div layer-name="Data visualization" style="'+bounds+'">'+clone.outerHTML+'</div>';
    }
    let out='';
    const name = el.getAttribute('aria-label') || el.id || el.classList[0] || el.tagName.toLowerCase();
    const style = bounds + spec.map(p=>p+':'+cs.getPropertyValue(p)).join(';')+';';
    for (const child of el.childNodes) {
      if (child.nodeType===1) { out+=render(child,box); continue; }
      if (child.nodeType!==3 || !child.textContent.trim()) continue;
      const range=document.createRange();range.selectNodeContents(child);
      const boxes=[...range.getClientRects()];
      if (!boxes.length) continue;
      // Keep a wrapped run as one editable text layer. The browser supplies its measured width.
      const first=boxes[0], width=boxes.length===1?first.width+1:box.right-first.left-parseFloat(cs.paddingRight);
      const height=cs.lineHeight==='normal'?parseFloat(cs.fontSize)*1.2:parseFloat(cs.lineHeight);
      const top=first.top-box.top-(height-first.height)/2;
      out+='<div style="position:absolute;left:'+px(first.left-box.left)+';top:'+px(top)+
        ';width:'+px(Math.max(1,width))+';line-height:'+cs.lineHeight+';color:'+cs.color+
        ';font-family:'+esc(cs.fontFamily)+';font-size:'+cs.fontSize+';font-weight:'+cs.fontWeight+
        ';letter-spacing:'+cs.letterSpacing+';text-transform:'+cs.textTransform+';">'+esc(child.textContent.trim())+'</div>';
    }
    if (el.matches('input,select')) {
      const val=el.matches('select')?el.selectedOptions[0].textContent:el.placeholder;
      out='<div style="position:absolute;left:9px;top:5px;color:'+cs.color+'">'+esc(val)+'</div>';
    }
    return '<div layer-name="'+esc(name)+'" style="'+esc(style)+'">'+out+'</div>';
  }
  const body=document.body, rect=body.getBoundingClientRect();
  const rootStyle='position:relative;box-sizing:border-box;width:'+px(rect.width)+';height:'+px(rect.height)+
    ';background:'+getComputedStyle(body).backgroundColor+';';
  return '<div layer-name="Dark Pool research desk" style="'+rootStyle+'">'+
    [...body.children].map(el=>render(el,rect)).join('')+'</div>';
}"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    out = folder / "paper"
    out.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.chrome)
        for label, width, tab, light in [
            ("desktop-session",1440,"session",False), ("mobile-session",390,"session",True),
            ("desktop-venues",1440,"venues",True), ("mobile-method",390,"method",True)
        ]:
            page = browser.new_page(viewport={"width":width, "height":960})
            page.emulate_media(reduced_motion="reduce")
            page.goto((folder / "preview.html").as_uri())
            if light:
                page.locator("#theme").click()
            page.locator(f'[data-tab="{tab}"]').click()
            markup = page.evaluate(CAPTURE)
            assert "layer-name=" in markup and "<script" not in markup
            assert "Dark Pool" in markup
            (out / f"{label}.html").write_text(markup,encoding="utf-8")
            print(label, len(markup), "characters", flush=True)
            page.close()
        browser.close()

if __name__ == "__main__":
    main()
