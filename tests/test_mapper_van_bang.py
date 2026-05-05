from app.core.mapper import map_extracted_data


def test_maps_book_number_when_ocr_header_says_degree_number():
    row = {
        "STT": "16",
        "Số hiệu bằng": "16-LKTQ K5",
        "Tên văn bằng": "Bà Mẫu mỹ惠",
        "GIỚI": "Nữ",
        "NGÀY SINH": "01/01/1991",
        "XẾP LOẠI": "Khá",
        "SỐ BẰNG": "506074",
        "NGÀY NHẬN": "4/6/2013",
        "KÝ, GHI TÊN": "周美惠",
    }

    mapped = map_extracted_data(row, "van_bang_dai_hoc")

    assert mapped["Số vào sổ gốc cấp văn bằng"] == "16-LKTQ K5"
    assert mapped["Số hiệu bằng"] == "506074"
    assert mapped["Ngày tháng năm cấp bằng"] == "04/06/2013"
    assert mapped["Họ, chữ đệm, tên người ký bằng"] == ""


def test_moves_name_with_title_without_space_from_degree_name_column():
    row = {
        "STT": "36",
        "Số hiệu bằng": "36-LKTQ K5",
        "Tên văn bằng": "Ông宋国",
        "Tên phiên âm": "Mr Song Guo",
        "GIỚI": "Nam",
        "NGÀY SINH": "03/06/1988",
        "XẾP LOẠI": "Khá",
        "SỐ BẰNG": "506094",
        "NGÀY NHẬN": "04/06/2013",
        "KÝ, GHI TÊN": "孙国",
    }

    mapped = map_extracted_data(row, "van_bang_dai_hoc")

    assert mapped["Tên văn bằng"] == ""
    assert mapped["Họ, chữ đệm và tên"] == "Ông宋国"
    assert mapped["Số hiệu bằng"] == "506094"


def test_repairs_shift_when_name_tail_looks_like_gender():
    row = {
        "STT": "77",
        "SÓ VÀO SÓ": "77/K45A1",
        "HỌ VÀ TÊN": "Hoàng Đức",
        "GIỚI": "Năm",
        "NGÀY SINH": "Nam",
        "XẾP LOẠI": "08/09/1991",
        "SÓ BẰNG": "Trung bình",
        "NGÀY NHẬN": "498608",
        "KÝ, GHI TÊN": "22/6/2013",
        "GHI CHÚ": "nam",
    }

    mapped = map_extracted_data(row, "van_bang_dai_hoc")

    assert mapped["Họ, chữ đệm và tên"] == "Hoàng Đức Năm"
    assert mapped["Giới tính"] == "Nam"
    assert mapped["Ngày, tháng, năm sinh"] == "08/09/1991"
    assert mapped["Xếp loại/hạng tốt nghiệp"] == "Trung bình"
    assert mapped["Số hiệu bằng"] == "498608"
    assert mapped["Ngày tháng năm cấp bằng"] == "22/06/2013"
    assert mapped["Họ, chữ đệm, tên người ký bằng"] == ""
    assert mapped["Ghi chú"] == ""


def test_maps_combined_degree_issue_header():
    row = {
        "STT": "159",
        "SỐ VÀO SỐ": "159/K45A3",
        "HỌ VÀ TÊN": "Ngô Bảo Ngọc",
        "GIỚI": "Nữ",
        "NGÀY SINH": "31/07/1991",
        "XẾP LOẠI": "Trung bình",
        "SỐ BÀNG NGÀY NHÂN": "498690",
        "KÝ, GHI TÊN": "22/6/113",
        "GHI CHÚ": "Ngọc",
    }

    mapped = map_extracted_data(row, "van_bang_dai_hoc")

    assert mapped["Số hiệu bằng"] == "498690"
    assert mapped["Số vào sổ gốc cấp văn bằng"] == "159/K45A3"
    assert mapped["Ngày tháng năm cấp bằng"] == "22/06/2013"
    assert mapped["Họ, chữ đệm, tên người ký bằng"] == ""


def test_repairs_fully_shifted_ocr_headers():
    row = {
        "STT": "364",
        "Số vào sổ gốc cấp văn bằng": "364/K45QA",
        "Hộ văn bằng": "Nguyễn Thu",
        "Giói": "Thuy",
        "NGAY SINGH": "Ng",
        "XẾP LOẠI": "01/12/1991",
        "Số BANG NGAY NHÂN": "Giói",
        "KY, GHI TÊN": "498895",
        "GHI CHÚ": "22/6/13",
    }

    mapped = map_extracted_data(row, "van_bang_dai_hoc")

    assert mapped["Họ, chữ đệm và tên"] == "Nguyễn Thu Thuy"
    assert mapped["Giới tính"] == "Nữ"
    assert mapped["Ngày, tháng, năm sinh"] == "01/12/1991"
    assert mapped["Xếp loại/hạng tốt nghiệp"] == "Giỏi"
    assert mapped["Số hiệu bằng"] == "498895"
    assert mapped["Ngày tháng năm cấp bằng"] == "22/06/2013"
    assert mapped["Họ, chữ đệm, tên người ký bằng"] == ""


def test_merges_name_tail_without_guessing_missing_gender():
    row = {
        "STT": "361",
        "Số vào sổ": "361/K45QA",
        "Hồ và tên": "Hoàng Thuy",
        "Giói": "Nga",
        "Ngày sinh": "26/03/1991",
        "Xếp loại": "Khả",
        "Số bằng ngày nhận": "498892",
        "Ký, Ghi tên": "22/6/2013",
        "Ghi chú": "Hoàng Thuy: H. H. H.",
    }

    mapped = map_extracted_data(row, "van_bang_dai_hoc")

    assert mapped["Họ, chữ đệm và tên"] == "Hoàng Thuy Nga"
    assert mapped["Giới tính"] == ""
    assert mapped["Số hiệu bằng"] == "498892"
    assert mapped["Ngày tháng năm cấp bằng"] == "22/06/2013"


def test_fills_missing_issue_year_from_same_batch():
    rows = [
        {
            "STT": "113",
            "Số vào sổ": "113/K45A2",
            "Họ và tên": "Nguyễn Văn Long",
            "Giới": "Nam",
            "Ngày sinh": "09/10/1991",
            "Xếp loại": "Khá",
            "Số bằng": "498644",
            "Ngày nhận": "22/06/13",
        },
        {
            "STT": "114",
            "Số vào sổ": "114/K45A2",
            "Họ và tên": "Trương Thị Mạnh",
            "Giới": "Nữ",
            "Ngày sinh": "23/02/1991",
            "Xếp loại": "Giỏi",
            "Số bằng": "498645",
            "Ngày nhận": "22/06",
        },
    ]

    mapped = map_extracted_data(rows, "van_bang_dai_hoc")

    assert mapped[0]["Ngày tháng năm cấp bằng"] == "22/06/2013"
    assert mapped[1]["Ngày tháng năm cấp bằng"] == "22/06/2013"
