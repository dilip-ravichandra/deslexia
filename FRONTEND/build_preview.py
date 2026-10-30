"""Build the standalone layout preview from the actual learner frontend."""
from pathlib import Path


def build():
    root = Path(__file__).resolve().parent
    html = (root / 'index.html').read_text(encoding='utf-8')
    css = (root / 'workspace.css').read_text(encoding='utf-8')
    marker = '<link rel="stylesheet" href="workspace.css">'
    if marker not in html:
        raise ValueError('Expected workspace stylesheet reference was not found')
    path = root / 'PREVIEW.html'
    preview = html.replace(marker, '<style>' + css + '</style>')
    preview = preview.replace('<script src="adaptive-controls.js"></script>', '<script>' + (root / 'adaptive-controls.js').read_text(encoding='utf-8') + '</script>')
    path.write_text(preview, encoding='utf-8')
    return path


if __name__ == '__main__':
    print(build())
