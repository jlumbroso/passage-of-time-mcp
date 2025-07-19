import pytest
from datetime import datetime, timedelta
import pytz
import sys
sys.path.insert(0, '.')
from passage_of_time_mcp import (
    parse_relative_day,
    parse_relative_time,
    parse_time_of_day
)
# Import the module to access the tool function
import passage_of_time_mcp

# Get the underlying function from the tool
parse_natural_time = passage_of_time_mcp.parse_natural_time.fn


class TestParseRelativeDay:
    def test_today(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_day("today", base)
        assert result == base

    def test_tomorrow(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_day("tomorrow", base)
        assert result.date() == (base + timedelta(days=1)).date()

    def test_yesterday(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_day("yesterday", base)
        assert result.date() == (base - timedelta(days=1)).date()

    def test_next_weekday(self):
        # Test from Monday (weekday=0)
        base = datetime(2024, 1, 15, 14, 30, 0)  # Monday
        result = parse_relative_day("next tuesday", base)
        assert result.weekday() == 1  # Tuesday
        assert result.date() == datetime(2024, 1, 16).date()

    def test_next_weekday_same_day(self):
        # Test "next monday" on a Monday
        base = datetime(2024, 1, 15, 14, 30, 0)  # Monday
        result = parse_relative_day("next monday", base)
        assert result.weekday() == 0  # Monday
        assert result.date() == datetime(2024, 1, 22).date()  # Next week

    def test_last_weekday(self):
        # Test from Monday
        base = datetime(2024, 1, 15, 14, 30, 0)  # Monday
        result = parse_relative_day("last friday", base)
        assert result.weekday() == 4  # Friday
        assert result.date() == datetime(2024, 1, 12).date()

    def test_this_weekday(self):
        # Test from Monday
        base = datetime(2024, 1, 15, 14, 30, 0)  # Monday
        result = parse_relative_day("this wednesday", base)
        assert result.weekday() == 2  # Wednesday
        assert result.date() == datetime(2024, 1, 17).date()

    def test_invalid_input(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_day("someday", base)
        assert result is None


class TestParseRelativeTime:
    def test_in_hours(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("in 2 hours", base)
        expected = base + timedelta(hours=2)
        assert result == expected

    def test_in_minutes(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("in 30 minutes", base)
        expected = base + timedelta(minutes=30)
        assert result == expected

    def test_days_ago(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("3 days ago", base)
        expected = base - timedelta(days=3)
        assert result == expected

    def test_weeks_ago(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("2 weeks ago", base)
        expected = base - timedelta(weeks=2)
        assert result == expected

    def test_in_months(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("in 2 months", base)
        # 2 months = approximately 60 days
        expected = base + timedelta(days=60)
        assert result == expected

    def test_singular_unit(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("in 1 hour", base)
        expected = base + timedelta(hours=1)
        assert result == expected

    def test_decimal_values(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("in 1.5 hours", base)
        expected = base + timedelta(hours=1.5)
        assert result == expected

    def test_invalid_input(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_relative_time("sometime later", base)
        assert result is None


class TestParseTimeOfDay:
    def test_noon(self):
        base = datetime(2024, 1, 15, 8, 30, 0)
        result = parse_time_of_day("noon", base)
        assert result.hour == 12
        assert result.minute == 0
        assert result.date() == base.date()

    def test_midnight(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_time_of_day("midnight", base)
        assert result.hour == 0
        assert result.minute == 0
        assert result.date() == base.date()

    def test_simple_am(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_time_of_day("9am", base)
        assert result.hour == 9
        assert result.minute == 0

    def test_simple_pm(self):
        base = datetime(2024, 1, 15, 8, 30, 0)
        result = parse_time_of_day("3pm", base)
        assert result.hour == 15
        assert result.minute == 0

    def test_with_minutes_am(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_time_of_day("9:30am", base)
        assert result.hour == 9
        assert result.minute == 30

    def test_with_minutes_pm(self):
        base = datetime(2024, 1, 15, 8, 30, 0)
        result = parse_time_of_day("3:45pm", base)
        assert result.hour == 15
        assert result.minute == 45

    def test_noon_pm(self):
        base = datetime(2024, 1, 15, 8, 30, 0)
        result = parse_time_of_day("12pm", base)
        assert result.hour == 12
        assert result.minute == 0

    def test_midnight_am(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_time_of_day("12am", base)
        assert result.hour == 0
        assert result.minute == 0

    def test_24_hour_format(self):
        base = datetime(2024, 1, 15, 8, 30, 0)
        result = parse_time_of_day("15:30", base)
        assert result.hour == 15
        assert result.minute == 30

    def test_invalid_hour(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_time_of_day("25:00", base)
        assert result is None

    def test_invalid_format(self):
        base = datetime(2024, 1, 15, 14, 30, 0)
        result = parse_time_of_day("teatime", base)
        assert result is None


class TestParseNaturalTime:
    def test_standard_timestamp(self):
        result = parse_natural_time("2024-01-15 14:30:00")
        assert result["timestamp"] == "2024-01-15 14:30:00"
        assert result["confidence"] == "high"
        assert "error" not in result

    def test_relative_day(self):
        # Mock current time
        ref_time = "2024-01-15 14:30:00"
        result = parse_natural_time("tomorrow", ref_time)
        assert "2024-01-16" in result["timestamp"]
        assert "14:30:00" in result["timestamp"]
        assert result["confidence"] == "high"
        assert "error" not in result

    def test_relative_time(self):
        ref_time = "2024-01-15 14:30:00"
        result = parse_natural_time("in 2 hours", ref_time)
        assert "2024-01-15 16:30:00" in result["timestamp"]
        assert result["confidence"] == "high"
        assert "error" not in result

    def test_time_of_day(self):
        ref_time = "2024-01-15 14:30:00"
        result = parse_natural_time("3pm", ref_time)
        assert "2024-01-15 15:00:00" in result["timestamp"]
        assert result["confidence"] == "high"
        assert "error" not in result

    def test_combined_expression(self):
        ref_time = "2024-01-15 14:30:00"
        result = parse_natural_time("tomorrow at 3pm", ref_time)
        assert "2024-01-16 15:00:00" in result["timestamp"]
        assert result["confidence"] == "high"
        assert "error" not in result

    def test_combined_with_noon(self):
        ref_time = "2024-01-15 14:30:00"
        result = parse_natural_time("next monday at noon", ref_time)
        assert "12:00:00" in result["timestamp"]
        assert result["confidence"] == "high"
        assert "error" not in result
        # Verify it's actually a Monday
        parsed_dt = datetime.strptime(result["timestamp"], "%Y-%m-%d %H:%M:%S")
        assert parsed_dt.weekday() == 0  # Monday

    def test_invalid_expression(self):
        result = parse_natural_time("sometime next week maybe")
        assert "error" in result
        assert result["confidence"] == "low"
        assert result["timestamp"] == ""

    def test_description_generation(self):
        ref_time = "2024-01-15 14:30:00"
        result = parse_natural_time("tomorrow at 3pm", ref_time)
        assert "tomorrow at 3:00 PM" in result["description"]

    def test_timezone_handling(self):
        ref_time = "2024-01-15 14:30:00"
        result = parse_natural_time("tomorrow", ref_time, timezone="US/Pacific")
        assert "error" not in result
        assert result["confidence"] == "high"

    def test_case_insensitive(self):
        ref_time = "2024-01-15 14:30:00"
        result1 = parse_natural_time("TOMORROW AT 3PM", ref_time)
        result2 = parse_natural_time("tomorrow at 3pm", ref_time)
        assert result1["timestamp"] == result2["timestamp"]
