"""اختبارات page_splitter."""

from pathlib import Path

from maani_alnahw import page_splitter


FIXT = Path(__file__).parent / "fixtures"


def test_split_zann_fixture_one_page(tmp_path):
    src = FIXT / "zann_page_sample.txt"
    tmp = tmp_path / "2.txt"
    tmp.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    pages = page_splitter.split_file(tmp)
    assert len(pages) == 1
    assert pages[0].part == 2
    assert pages[0].page == 5
    assert "ظن وأخواتها" in pages[0].raw_text or "طن وأخواتها" in pages[0].raw_text


def test_infer_part():
    assert page_splitter._infer_part("1.txt") == 1
    assert page_splitter._infer_part("4.txt") == 4
    assert page_splitter._infer_part("xyz.txt") == 0


def test_split_real_part2():
    """يَتَأَكَّد أَنّ الجُزء 2 الحَقيقيّ يَنقَسِم."""
    project_root = Path(__file__).parent.parent
    raw = project_root / "data" / "raw" / "maani_alnahw" / "2.txt"
    if not raw.exists():
        return
    pages = page_splitter.split_file(raw)
    assert len(pages) > 100
    assert all(p.part == 2 for p in pages)
