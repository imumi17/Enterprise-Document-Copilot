from ingest.html_to_markdown import html_to_markdown


def test_html_to_markdown_strips_tags_and_hidden_blocks():
    html = (
        b"<html><body>"
        b"<div style=\"display:none\">hidden metadata</div>"
        b"<p>Revenue increased in fiscal 2025.</p>"
        b"<div>Data center demand remained strong.</div>"
        b"</body></html>"
    )
    markdown = html_to_markdown(html)
    assert "hidden metadata" not in markdown
    assert "Revenue increased in fiscal 2025." in markdown
    assert "Data center demand remained strong." in markdown
