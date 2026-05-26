"""اختبارات topic_detector."""

from maani_alnahw import topic_detector


def test_zann_detected_in_clean_text():
    pages = [{
        "part": 2, "page": 5,
        "raw_text": "طن وأخواتها\nتدخل ظن وأخواتها على المبتدأ والخبر",
        "cleaned_text": "ظن وأخواتها\nتدخل ظن وأخواتها على المبتدأ والخبر",
        "doc_id": "test", "source_file": "2.txt",
    }]
    det = topic_detector.TopicDetector()
    topics = det.detect(pages)
    assert any(t.title == "ظن وأخواتها" for t in topics)


def test_topic_has_confidence():
    pages = [{
        "part": 2, "page": 5,
        "cleaned_text": "ظن وأخواتها",
        "raw_text": "ظن وأخواتها",
        "doc_id": "test", "source_file": "2.txt",
    }]
    det = topic_detector.TopicDetector()
    topics = det.detect(pages)
    assert all(t.confidence > 0 for t in topics)
