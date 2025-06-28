import os
import mimetypes
import html


from fs import IOSYSFileSystem


def get_raw_url(path: str):
    return f"http://localhost:{os.environ['MAIN_SERVER_PORT']}/raw?path={path}"


def render_preview_html(fs: IOSYSFileSystem, path: str):
    node = fs.get_node(path)
    if not node:
        return f"<p>Error: File not found: {path}</p>"

    if node.get_meta("type") == "directory":
        child_num = len(node.children())
        return f'<p>Directory with <code style="font-size: larger">{child_num}</code> children</p>'

    mine_type = mimetypes.guess_type(path)[0] or ""

    if mine_type.startswith("image/"):
        return render_image(path)
    elif mine_type.startswith("text/"):
        return render_plain_text(node.read().decode("utf-8"))
    elif mine_type.startswith("video/"):
        return render_video(path)
    elif mine_type.startswith("audio/"):
        return render_audio(path)
    else:
        return f"<p>Preview not available for {path}</p>"


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
    if not content:
        return """
        <p style="color: gray; font-style: italic;">(Empty)</p>
        """
    if len(content) > 1000:
        content = (
            content[:1000] + f"\n\n... (truncated {len(content) - 1000} characters)"
        )
    content = html.escape(content)
    return f"""
<pre>{content}</pre>
"""
