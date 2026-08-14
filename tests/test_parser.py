import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser import extract_date


def test_chinese_month_day():
    d, warns = extract_date("活动时间：8月15日 19:00", date(2026, 7, 1))
    assert d == date(2026, 8, 15)
    assert any("没有年份" in w for w in warns)


def test_chinese_month_day_no_ri():
    d, warns = extract_date("8月15号晚上见", date(2026, 7, 1))
    assert d == date(2026, 8, 15)


def test_chinese_with_year():
    d, _ = extract_date("2026年9月3日举办", date(2026, 7, 1))
    assert d == date(2026, 9, 3)


def test_chinese_no_year_uses_base():
    d, warns = extract_date("8月15日开演", date(2026, 7, 1))
    assert d == date(2026, 8, 15)
    assert "没有年份" in warns[0]


def test_passed_date_infers_next_year():
    d, warns = extract_date("8月15日开演", date(2026, 9, 1))
    assert d == date(2027, 8, 15)
    assert "明年" in warns[0]


def test_slash_format():
    d, _ = extract_date("2026/8/15 15:00", date(2026, 7, 1))
    assert d == date(2026, 8, 15)


def test_mm_dd_no_year():
    d, _ = extract_date("8/15", date(2026, 7, 1))
    assert d == date(2026, 8, 15)


def test_english_full_month():
    d, _ = extract_date("August 15, 2026", date(2026, 7, 1))
    assert d == date(2026, 8, 15)


def test_english_abbr_month():
    d, _ = extract_date("Aug 15 2026", date(2026, 7, 1))
    assert d == date(2026, 8, 15)


def test_english_day_first():
    d, _ = extract_date("15 Aug 2026", date(2026, 7, 1))
    assert d == date(2026, 8, 15)


def test_relative_today_tomorrow():
    base = date(2026, 8, 14)
    d, _ = extract_date("明天下午有活动", base)
    assert d == date(2026, 8, 15)
    d, _ = extract_date("今天见", base)
    assert d == date(2026, 8, 14)


def test_relative_weekday_chinese():
    base = date(2026, 8, 14)  # 周五
    d, _ = extract_date("下周五聚会", base)
    assert d == date(2026, 8, 21)
    d, _ = extract_date("本周日演出", base)
    assert d == date(2026, 8, 16)


def test_multiple_dates_warns():
    d, warns = extract_date("8月15日或8月20日", date(2026, 7, 1))
    assert d == date(2026, 8, 15)
    assert any("多个候选" in w for w in warns)


def test_no_date_returns_none():
    assert extract_date("欢迎来到现场", date(2026, 7, 1)) is None


from datetime import time

from parser import extract_time


def test_24h_time():
    assert extract_time("19:00 开始") == (time(19, 0), None)


def test_24h_range():
    start, end = extract_time("19:00-21:00")
    assert start == time(19, 0) and end == time(21, 0)


def test_24h_range_tilde():
    start, end = extract_time("19:00~21:00")
    assert start == time(19, 0) and end == time(21, 0)


def test_pm_format():
    start, _ = extract_time("7:00PM")
    assert start == time(19, 0)


def test_am_format_lower():
    start, _ = extract_time("9:30am")
    assert start == time(9, 30)


def test_chinese_period_evening():
    start, _ = extract_time("晚上7点")
    assert start == time(19, 0)


def test_chinese_period_afternoon():
    start, _ = extract_time("下午3点半")
    assert start == time(15, 30)


def test_chinese_period_morning():
    start, _ = extract_time("上午9点30分")
    assert start == time(9, 30)


def test_chinese_period_noon():
    start, _ = extract_time("中午12点")
    assert start == time(12, 0)


def test_chinese_midnight():
    start, _ = extract_time("凌晨1点")
    assert start == time(1, 0)


def test_no_time_returns_none():
    assert extract_time("欢迎来到现场") is None


from datetime import datetime, timedelta

from parser import Event, parse_event


def test_full_chinese_event():
    text = "城市音乐节\n地点：人民广场\n时间：8月15日 19:00-21:00\n票价免费"
    ev = parse_event(text, base_date=datetime(2026, 7, 1))
    assert ev.title == "城市音乐节"
    assert ev.start == datetime(2026, 8, 15, 19, 0)
    assert ev.end == datetime(2026, 8, 15, 21, 0)
    assert ev.location == "人民广场"
    assert ev.description == text


def test_default_duration_two_hours():
    ev = parse_event("讲座 9月2日 10:00", base_date=datetime(2026, 7, 1))
    assert ev.start == datetime(2026, 9, 2, 10, 0)
    assert ev.end == datetime(2026, 9, 2, 12, 0)


def test_title_from_largest_font_line():
    text = "小字内容\n演唱会之夜\n8月15日 19:00"
    lines = [
        {"text": "小字内容", "height": 20},
        {"text": "演唱会之夜", "height": 90},
        {"text": "8月15日 19:00", "height": 30},
    ]
    ev = parse_event(text, lines=lines, base_date=datetime(2026, 7, 1))
    assert ev.title == "演唱会之夜"


def test_title_falls_back_to_first_line():
    ev = parse_event("周末读书会\n8月20日 14:00", base_date=datetime(2026, 7, 1))
    assert ev.title == "周末读书会"


def test_location_english_venue():
    ev = parse_event("Tech Meetup\nVenue: Apple Park\nAug 15 2026 19:00", base_date=datetime(2026, 7, 1))
    assert ev.location == "Apple Park"


def test_location_wechat_at_prefix():
    ev = parse_event("live show\n@三里屯太古里\n8月15日 19:00", base_date=datetime(2026, 7, 1))
    assert ev.location == "三里屯太古里"


def test_missing_date_sets_start_none():
    ev = parse_event("欢迎光临", base_date=datetime(2026, 7, 1))
    assert ev.start is None and ev.end is None
    assert any("日期" in w for w in ev.warnings)


def test_missing_time_uses_midday_default():
    ev = parse_event("义卖活动 8月15日", base_date=datetime(2026, 7, 1))
    assert ev.start == datetime(2026, 8, 15, 0, 0)
    assert ev.end == datetime(2026, 8, 15, 2, 0)


def test_non_month_word_with_number_ignored():
    base = date(2026, 7, 1)
    d, warns = extract_date("Room 15\nLocation 200\nAug 20 开始", base)
    assert d == date(2026, 8, 20)


def test_location_line_with_number_does_not_crash():
    ev = parse_event("Live Show\nVenue: loc 200\nAug 15 2026 19:00", base_date=datetime(2026, 7, 1))
    assert ev.start == datetime(2026, 8, 15, 19, 0)
    assert ev.location == "loc 200"


def test_us_mm_dd_yy_date():
    d, warns = extract_date("08-20-26", date(2026, 7, 1))
    assert d == date(2026, 8, 20)
    assert warns == []


def test_us_mm_dd_yy_1990s():
    d, _ = extract_date("12-25-99", date(2026, 7, 1))
    assert d == date(1999, 12, 25)


def test_us_mm_dd_yyyy_date():
    d, _ = extract_date("08-20-2026", date(2026, 7, 1))
    assert d == date(2026, 8, 20)


def test_explicit_past_year_not_shifted():
    d, warns = extract_date("08-20-26", date(2026, 9, 1))
    assert d == date(2026, 8, 20)
    assert warns == []


def test_time_single_letter_pm():
    start, _ = extract_time("05:00p")
    assert start == time(17, 0)


def test_time_single_letter_pm_thirteen():
    start, _ = extract_time("01:30p")
    assert start == time(13, 30)


def test_time_single_letter_am():
    start, _ = extract_time("10:00a")
    assert start == time(10, 0)


SCHEDULE_TEXT = (
    "Appointments From: 08-12-26 for Vike Lin\n"
    "Location: MA-Malden-BSPT\n"
    "1\nThu\n08-20-26\n05:00p\nPT Daily\nTreatment\nMA-Malden-\nBSPT\n"
    "2\nTue\n08-25-26\n01:30p\nPT Daily\nTreatment\nMA-Malden-\nBSPT\n"
    "3\nThu\n09-03-26\n02:00p\nPT Daily\nTreatment\nMA-Malden-\nBSPT"
)


def test_multi_event_schedule():
    from parser import parse_events
    evs = parse_events(SCHEDULE_TEXT, base_date=datetime(2026, 7, 1))
    assert len(evs) == 3
    assert evs[0].start == datetime(2026, 8, 20, 17, 0)
    assert evs[0].end == datetime(2026, 8, 20, 19, 0)
    assert evs[1].start == datetime(2026, 8, 25, 13, 30)
    assert evs[2].start == datetime(2026, 9, 3, 14, 0)
    assert evs[0].title == "PT Daily Treatment"
    assert evs[2].title == "PT Daily Treatment"
    assert all(e.location == "MA-Malden-BSPT" for e in evs)
    assert all(e.end and e.end > e.start for e in evs)


def test_parse_events_single_event_falls_back():
    from parser import parse_events
    evs = parse_events("城市音乐节\n地点：人民广场\n时间：8月15日 19:00-21:00", base_date=datetime(2026, 7, 1))
    assert len(evs) == 1
    assert evs[0].title == "城市音乐节"
    assert evs[0].start == datetime(2026, 8, 15, 19, 0)
