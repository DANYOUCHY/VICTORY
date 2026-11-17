"""Writing built pages into site/, or only comparing them with what is there."""
from pathlib import Path


def current_text(path: Path) -> str:
    """What site/ holds now ('' if the file does not exist yet)."""
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def first_difference(old: str, new: str) -> str:
    """A short pointer to where two versions part, for the report."""
    i = next((n for n, (a, b) in enumerate(zip(old, new)) if a != b), min(len(old), len(new)))
    line = old.count('\n', 0, i) + 1
    return f'line {line}: site has {old[i:i + 60]!r}, build has {new[i:i + 60]!r}'


def write_page(path: Path, html: str) -> bool:
    """Write the page with LF line ends. True if the file changed."""
    if current_text(path) == html:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    return True
