import os
import mimetypes

from fs import IOSYSFileSystem


def get_raw_url(path: str):
    return f"http://localhost:{os.environ['MAIN_SERVER_PORT']}/raw?path={path}"


def render_preview_html(fs: IOSYSFileSystem, path: str):
    node = fs.get_node(path)
    if not node:
        return f"<p>Error: File not found: {path}</p>"

    mine_type = mimetypes.guess_type(path)[0] or ""

    if mine_type.startswith("image/"):
        body = render_image(path)
    elif mine_type.startswith("text/"):
        body = render_plain_text(node.read().decode("utf-8"))
    elif mine_type.startswith("video/"):
        body = render_video(path)
    elif mine_type.startswith("audio/"):
        body = render_audio(path)
    else:
        body = f"<p>Preview not available for {path}</p>"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body, body > * {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    {body}
</body>
</html>
"""


def render_image(path: str):
    return f"""
<img src="{get_raw_url(path)}" alt="{path}" style="width:100%">
"""


def render_video(path: str):
    return f"""
<video controls style="width:100%" src="{get_raw_url(path)}" />
"""


def render_audio(path: str):
    return f"""
<audio controls style="width:100%" src="{get_raw_url(path)}" />
"""


def render_plain_text(content: str):
    return f"""
<pre>{content}</pre>
"""
