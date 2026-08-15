from ingest.chunking import chunk_markdown, split_sections, split_text_window


def test_split_text_window_overlap():
    text = "alpha beta gamma delta epsilon zeta eta theta"
    chunks = split_text_window(text, chunk_size=20, overlap=5)
    assert len(chunks) >= 2
    assert "alpha" in chunks[0]


def test_chunk_markdown_assigns_section_metadata():
    markdown = "Intro paragraph.\n\nITEM 1. Business\n\nRevenue grew in fiscal 2025."
    chunks = chunk_markdown(
        markdown,
        base_metadata={"ticker": "NVDA", "fiscal_year": 2025},
        chunk_size=80,
        chunk_overlap=10,
    )
    assert chunks
    assert chunks[-1].metadata["ticker"] == "NVDA"
    assert any(chunk.section and "ITEM 1" in chunk.section for chunk in chunks)


def test_split_sections_detects_item_headings():
    markdown = "Preface\n\nITEM 1A. Risk Factors\n\nSupply risk increased."
    sections = split_sections(markdown)
    assert len(sections) >= 2
    assert sections[1][0] == "ITEM 1A. Risk Factors"
