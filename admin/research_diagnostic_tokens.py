"""Project canonical root tokens into the bounded diagnostic section only."""
from pathlib import Path
import re

_SOURCE = Path(__file__).resolve().parents[1] / "templates" / "theme.css"
_SELECTORS = {
    ":root": ".rf-diagnostics",
    'html[data-theme="light"]': '.rf-diagnostics[data-theme="light"]',
    'html[data-theme="dark"]': '.rf-diagnostics[data-theme="dark"]',
    'html[data-lang="zh"]': '.rf-diagnostics[data-lang="zh"]',
    'html[data-theme="light"][data-lang="zh"]': '.rf-diagnostics[data-theme="light"][data-lang="zh"]',
    'html[data-theme="dark"][data-lang="zh"]': '.rf-diagnostics[data-theme="dark"][data-lang="zh"]',
}


def project_tokens(source: str) -> bytes:
    if type(source) is not str or len(source) > 1024 * 1024:
        raise ValueError("canonical token source unavailable")
    text = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    depth, start, selector, output = 0, 0, None, []
    # Canonical root blocks have literal scalar/function token declarations.
    # Nested at-rules and component selectors cannot escape this projection.
    quote, escaped = None, False
    for i, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == "{" and depth == 0:
            selector = _SELECTORS.get(text[start:i].strip())
            start = i + 1
            depth = 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("malformed canonical token source")
            if depth == 0:
                body = text[start:i]
                if selector and "{" not in body and "}" not in body:
                    declarations = []
                    for declaration in body.split(";"):
                        key, sep, value = declaration.partition(":")
                        key, value = key.strip(), value.strip()
                        if sep and re.fullmatch(r"--[A-Za-z0-9_-]+", key) and value:
                            declarations.append(key + ":" + value + ";")
                    if declarations:
                        output.append(selector + "{" + "".join(declarations) + "}")
                start = i + 1
                selector = None
        elif char == ";" and depth == 0:
            start = i + 1
    if depth or quote or not output:
        raise ValueError("canonical token source incomplete")
    return ("\n".join(output) + "\n").encode()


def stylesheet() -> bytes:
    with _SOURCE.open("r", encoding="utf-8") as stream:
        source = stream.read(1024 * 1024 + 1)
    return project_tokens(source)
