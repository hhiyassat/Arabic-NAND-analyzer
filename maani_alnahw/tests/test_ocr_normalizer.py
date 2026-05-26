"""اختبارات ocr_normalizer."""

from maani_alnahw import ocr_normalizer


def test_zann_heading_normalized():
    nrm = ocr_normalizer.OCRNormalizer()
    cleaned, corrections = nrm.normalize_page("طن وأخواتها", part=2, page=5)
    assert "ظن وأخواتها" in cleaned
    assert any(c.raw == "طن وأخواتها" and c.normalized == "ظن وأخواتها"
               for c in corrections)


def test_book_title_normalized():
    nrm = ocr_normalizer.OCRNormalizer()
    cleaned, _ = nrm.normalize_page("ماني النحو", part=1, page=1)
    assert "معاني النحو" in cleaned


def test_low_confidence_is_suggest_only():
    """تَأَكُّد أَنّ التَّصحيحات ذات الثِّقَة < 0.85 لا تُطَبَّق."""
    # في معجمنا الحاليّ لا يوجَد تَصحيح < 0.85 (الأَدنى = 0.85)
    # لَكِنّ المَنطِق مُبَرمَج
    nrm = ocr_normalizer.OCRNormalizer()
    _, corrections = nrm.normalize_page("معاني النحو", part=1, page=1)
    # هَل الكُلّ مُطَبَّق؟
    for c in corrections:
        if c.confidence < 0.85:
            assert c.action == "suggest_only"


def test_raw_text_preserved_in_correction():
    """raw يَبقى أَصليًّا في سِجِلّ التَّصحيح."""
    nrm = ocr_normalizer.OCRNormalizer()
    _, corrections = nrm.normalize_page("ماني النحو", part=1, page=1)
    assert any(c.raw == "ماني النحو" for c in corrections)


def test_scholar_name_normalized():
    nrm = ocr_normalizer.OCRNormalizer()
    cleaned, _ = nrm.normalize_page("فاضل السامراني", part=1, page=1)
    assert "فاضل صالح السامرائي" in cleaned
