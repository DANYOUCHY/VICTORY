"""The site's template language. Kept tiny on purpose, so anyone can read it.

Three forms, nothing else:

    {{name}}                          a parameter (from the page's page.json, or from an include)
    {{> path/file.html}}              the contents of another source file (path from src/)
    {{> path/file.html key=value}}    the same, with parameters for that file only

A source file's single final newline is not part of its content (editors add it).
"""
import re
from pathlib import Path

INCLUDE = re.compile(r'\{\{>\s*([^\s}]+)((?:\s+[\w-]+=[^\s}]*)*)\s*\}\}')
PARAM = re.compile(r'\{\{([\w-]+)\}\}')
ARG = re.compile(r'([\w-]+)=([^\s}]*)')
MAX_DEPTH = 10


class TemplateError(Exception):
    """A source file asks for something that does not exist."""


def read_source(path: Path) -> str:
    """Read a source file as the text it stands for."""
    text = path.read_text(encoding='utf-8').replace('\r\n', '\n')
    return text[:-1] if text.endswith('\n') else text


def fill_params(text: str, params: dict, where: str) -> str:
    """Replace every {{name}} with its value; a missing value is an error, never a blank."""
    def value(match):
        name = match.group(1)
        if name not in params:
            raise TemplateError(f'{where}: no value for {{{{{name}}}}}')
        return str(params[name])
    return PARAM.sub(value, text)


def render(text: str, params: dict, src_root: Path, where: str = 'page', depth: int = 0) -> str:
    """Fill the parameters of this text, then put each included file in its place."""
    if depth > MAX_DEPTH:
        raise TemplateError(f'{where}: includes nested too deep (does a file include itself?)')
    text = fill_params(text, params, where)

    def include(match):
        rel = match.group(1)
        path = src_root / rel
        if not path.is_file():
            raise TemplateError(f'{where}: missing file {rel}')
        local = {**params, **dict(ARG.findall(match.group(2)))}
        return render(read_source(path), local, src_root, rel, depth + 1)

    return INCLUDE.sub(include, text)
