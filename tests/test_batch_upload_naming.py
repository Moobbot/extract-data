from app.api.routes import _safe_batch_filename


def test_safe_batch_filename_preserves_sortable_upload_order():
    assert (
        _safe_batch_filename("Quet so bang/Trang000010.jpg", 2)
        == "00002_Trang000010.jpg"
    )
    assert _safe_batch_filename("bad:name?.png", 12) == "00012_bad_name.png"
