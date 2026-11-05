"""Keep production URL semantics while serving static assets from the source tree."""
import re
from urllib.parse import urljoin

_ASSET = re.compile(r"(<(?:script|img|link)\b[^>]*?\b(?:src|href)=)([\"'])([^\"']+)\2", re.I)


def bind_template_assets(html):
    # A document-wide <base> also changes history.pushState/replaceState and
    # hash destinations. Rebind only asset attributes; leave links/routes intact.
    def replace(match):
        path = match.group(3)
        if path.startswith(("/", "#", "data:", "http:", "https:")):
            return match.group(0)
        # The public runtime config is a built site asset, not a template file.
        base = "/site/" if path.split("?", 1)[0] in ("live_config.js", "./live_config.js") else "/templates/"
        return match.group(1) + match.group(2) + urljoin(base, path) + match.group(2)
    return _ASSET.sub(replace, html)
