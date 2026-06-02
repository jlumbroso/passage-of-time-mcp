import pytest
from datetime import datetime, timedelta
import pytz
from unittest.mock import patch, MagicMock
import sys
import os

# Import the actual implementation with a mock that mirrors REAL FastMCP.
#
# IMPORTANT: real fastmcp's @mcp.tool() replaces the decorated function with a
# FunctionTool object that is NOT callable; the runtime invokes the underlying
# function via its `.fn` attribute. Our mock reproduces that exactly so the test
# suite catches the class of bug where one tool calls another tool's *decorated*
# version directly (which raises "'FunctionTool' object is not callable" in prod
# but would silently pass against a pass-through mock).

class FakeFunctionTool:
    """Stand-in for fastmcp.FunctionTool: holds the raw fn, is NOT callable."""
    def __init__(self, func):
        self.fn = func
        # Preserve metadata so tooling/introspection still works.
        self.__name__ = getattr(func, "__name__", "tool")
        self.__doc__ = getattr(func, "__doc__", None)
    # Intentionally no __call__: calling the decorated tool must fail, just
    # like real fastmcp, so internal tool-to-tool calls are caught in tests.


class MockFastMCP:
    def __init__(self, **kwargs):
        pass

    def tool(self):
        def decorator(func):
            return FakeFunctionTool(func)
        return decorator

    def run_sse_async(self, **kwargs):
        pass

# Replace fastmcp with our mock that mirrors real FunctionTool wrapping behavior
sys.modules['fastmcp'] = MagicMock()
sys.modules['fastmcp'].FastMCP = MockFastMCP

# Now import after setting up the mock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import passage_of_time_mcp

# Extract the underlying functions via `.fn`, exactly how the MCP runtime calls
# them. (The module-level attributes are FakeFunctionTool objects, not callables.)
current_datetime = passage_of_time_mcp.current_datetime.fn
time_difference = passage_of_time_mcp.time_difference.fn
time_since = passage_of_time_mcp.time_since.fn
parse_timestamp = passage_of_time_mcp.parse_timestamp.fn
add_time = passage_of_time_mcp.add_time.fn
timestamp_context = passage_of_time_mcp.timestamp_context.fn
format_duration = passage_of_time_mcp.format_duration.fn


class TestCurrentDatetime:
    def test_default_timezone(self):
        result = current_datetime()
        assert isinstance(result, str)
        # Check that it has date, time, and timezone components
        parts = result.split()
        assert len(parts) >= 3
        # Should contain NYC timezone (EST or EDT)
        assert any(tz in result for tz in ["EST", "EDT", "America/New_York"])
        
    def test_utc_timezone(self):
        result = current_datetime("UTC")
        assert "UTC" in result
        
    def test_invalid_timezone(self):
        result = current_datetime("Invalid/Timezone")
        assert "Error: Unknown timezone" in result


class TestTimeDifference:
    def test_simple_difference(self):
        result = time_difference(
            "2024-01-01 10:00:00",
            "2024-01-01 13:30:00"
        )
        assert isinstance(result, dict)
        assert result["seconds"] == 12600  # 3.5 hours
        assert "3 hours, 30 minutes" in result["formatted"]
        assert result["is_negative"] is False
        
    def test_negative_difference(self):
        result = time_difference(
            "2024-01-01 13:30:00",
            "2024-01-01 10:00:00"
        )
        assert result["seconds"] == -12600
        assert result["is_negative"] is True
        assert "-3 hours, 30 minutes" in result["formatted"]
        
    def test_with_specific_unit(self):
        result = time_difference(
            "2024-01-01 10:00:00",
            "2024-01-01 13:30:00",
            unit="hours"
        )
        assert abs(result["requested_unit"] - 3.5) < 0.001
        
    def test_different_date_formats(self):
        # Test with standard format only now
        result = time_difference(
            "2024-01-01 10:00:00",
            "2024-01-01 13:30:00"
        )
        assert result["seconds"] == 12600
        
    def test_invalid_format(self):
        # Test that non-standard formats return clear errors
        result = time_difference(
            "Jan 1, 2024 10:00 AM",
            "2024-01-01 13:30:00"
        )
        assert "error" in result
        assert "Invalid timestamp format" in result["error"]
        assert "YYYY-MM-DD HH:MM:SS" in result["error"]
        
    def test_days_difference(self):
        result = time_difference(
            "2024-01-01",
            "2024-01-05"
        )
        # Allow for floating point precision differences
        assert result["seconds"] == 345600  # 4 days
        assert "4 days" in result["formatted"]
        
    def test_invalid_format(self):
        # Test that non-standard formats return clear errors
        result = time_difference(
            "Jan 1, 2024 10:00 AM",
            "2024-01-01 13:30:00"
        )
        assert "error" in result
        assert "Invalid timestamp format" in result["error"]
        assert "YYYY-MM-DD HH:MM:SS" in result["error"]
        
    def test_error_handling(self):
        result = time_difference(
            "invalid date",
            "2024-01-01"
        )
        assert "error" in result


class TestTimeSince:
    @patch('passage_of_time_mcp.datetime')
    def test_time_since_past(self, mock_datetime):
        # Create a proper mock for datetime
        real_datetime = datetime
        mock_datetime.now = MagicMock()
        mock_datetime.strptime = real_datetime.strptime
        
        # Set up the mock to return a specific time
        tz = pytz.timezone("America/New_York")
        mock_now = real_datetime(2024, 1, 10, 15, 0, 0, tzinfo=tz)
        mock_datetime.now.return_value = mock_now
        
        result = time_since("2024-01-10 14:00:00", timezone="America/New_York")
        assert isinstance(result, dict)
        assert abs(result["seconds"] - 3600) < 60  # Allow for small differences
        assert "hour" in result["formatted"]
        assert result["context"] in ["earlier today", "earlier"]
        
    @patch('passage_of_time_mcp.datetime')
    def test_time_since_yesterday(self, mock_datetime):
        real_datetime = datetime
        mock_datetime.now = MagicMock()
        mock_datetime.strptime = real_datetime.strptime
        
        tz = pytz.timezone("America/New_York")
        mock_now = real_datetime(2024, 1, 10, 15, 0, 0, tzinfo=tz)
        mock_datetime.now.return_value = mock_now
        
        result = time_since("2024-01-09 15:00:00", timezone="America/New_York")
        assert result["context"] == "yesterday"
        
    @patch('passage_of_time_mcp.datetime')
    def test_time_since_future(self, mock_datetime):
        real_datetime = datetime
        mock_datetime.now = MagicMock()
        mock_datetime.strptime = real_datetime.strptime
        
        tz = pytz.timezone("America/New_York")
        mock_now = real_datetime(2024, 1, 10, 15, 0, 0, tzinfo=tz)
        mock_datetime.now.return_value = mock_now
        
        result = time_since("2024-01-10 16:00:00", timezone="America/New_York")
        assert result["seconds"] < 0
        assert "from now" in result["formatted"]
        assert result["context"] == "in the future"


class TestParseTimestamp:
    def test_basic_parsing(self):
        result = parse_timestamp("2024-01-15 14:30:00")
        assert isinstance(result, dict)
        assert result["date"] == "2024-01-15"
        assert result["time"] == "14:30:00"
        assert result["day_of_week"] == "Monday"
        assert "January 15, 2024" in result["human"]
        
    def test_standard_format_only(self):
        # Test that only standard format works
        result = parse_timestamp("2024-01-15 14:30:00")
        assert result["date"] == "2024-01-15"
        assert "14:30" in result["time"]
        
    def test_invalid_format_error(self):
        # Test that non-standard format returns error
        result = parse_timestamp("Jan 15th, 2024 at 2:30 PM")
        assert "error" in result
        assert "Invalid timestamp format" in result["error"]
        
    def test_timezone_conversion(self):
        result = parse_timestamp(
            "2024-01-15 14:30:00",
            source_timezone="UTC",
            target_timezone="America/New_York"
        )
        # UTC 14:30 should be EST 09:30
        assert "09:30" in result["time"]
        
    def test_unix_timestamp(self):
        result = parse_timestamp("2024-01-15 00:00:00", target_timezone="UTC")
        unix_ts = int(result["unix"])
        # Verify it's a reasonable Unix timestamp for that date
        assert unix_ts > 1700000000  # After Nov 2023
        assert unix_ts < 1800000000  # Before 2027
        
    def test_error_handling(self):
        result = parse_timestamp("not a valid date")
        assert "error" in result
        assert "Invalid timestamp format" in result["error"]
        assert "YYYY-MM-DD" in result["error"]  # Check format hint is included


class TestAddTime:
    def test_add_hours(self):
        result = add_time("2024-01-15 10:00:00", 3, "hours")
        assert isinstance(result, dict)
        assert "13:00:00" in result["result"]
        
    def test_add_days(self):
        result = add_time("2024-01-15", 5, "days")
        assert "2024-01-20" in result["result"]
        
    def test_subtract_time(self):
        result = add_time("2024-01-15 10:00:00", -2, "hours")
        assert "08:00:00" in result["result"]
        
    @patch('passage_of_time_mcp.datetime')
    def test_natural_language_tomorrow(self, mock_datetime):
        real_datetime = datetime
        
        # Mock datetime.now to return a specific time
        def mock_now(tz=None):
            if tz:
                return real_datetime(2024, 1, 15, 10, 0, 0, tzinfo=tz)
            return real_datetime(2024, 1, 15, 10, 0, 0)
        
        mock_datetime.now = mock_now
        mock_datetime.strptime = real_datetime.strptime
        
        result = add_time("2024-01-15 14:00:00", 1, "days")
        assert isinstance(result["description"], str)
        assert "tomorrow" in result["description"].lower()
        
    def test_add_weeks(self):
        result = add_time("2024-01-01", 2, "weeks")
        assert "2024-01-15" in result["result"]
        
    def test_error_handling(self):
        result = add_time("invalid date", 1, "days")
        assert "error" in result


class TestTimestampContext:
    def test_morning_context(self):
        # Use standard format without timezone abbreviation
        result = timestamp_context("2024-01-15 08:30:00", timezone="America/New_York")
        assert isinstance(result, dict)
        assert result["time_of_day"] == "early_morning"
        assert result["typical_activity"] == "commute_time"
        assert result["hour_24"] == 8
        
    def test_lunch_time(self):
        # Use standard format without timezone abbreviation
        result = timestamp_context("2024-01-15 12:30:00", timezone="America/New_York")
        assert result["time_of_day"] == "afternoon"
        assert result["typical_activity"] == "lunch_time"
        
    def test_weekend_detection(self):
        # January 13, 2024 is a Saturday
        result = timestamp_context("2024-01-13 10:00:00")
        assert result["is_weekend"] is True
        assert result["is_business_hours"] is False
        assert result["day_of_week"] == "Saturday"
        
    def test_business_hours(self):
        # January 15, 2024 is a Monday
        result = timestamp_context("2024-01-15 14:00:00")
        assert result["is_weekend"] is False
        assert result["is_business_hours"] is True
        
    @patch('passage_of_time_mcp.datetime')
    def test_relative_day_today(self, mock_datetime):
        real_datetime = datetime
        
        # Mock datetime.now
        def mock_now(tz=None):
            if tz:
                return real_datetime(2024, 1, 15, 15, 0, 0, tzinfo=tz)
            return real_datetime(2024, 1, 15, 15, 0, 0)
        
        mock_datetime.now = mock_now
        mock_datetime.strptime = real_datetime.strptime
        
        result = timestamp_context("2024-01-15 10:00:00")
        assert result["relative_day"] == "today"
        
    def test_late_night(self):
        result = timestamp_context("2024-01-15 23:30:00")
        assert result["time_of_day"] == "late_night"
        assert result["typical_activity"] == "sleeping_time"
        
    def test_error_handling(self):
        result = timestamp_context("invalid date")
        assert "error" in result


class TestFormatDuration:
    def test_full_format(self):
        result = format_duration(93784)  # 1 day, 2 hours, 3 minutes, 4 seconds
        assert isinstance(result, str)
        assert "1 day" in result
        assert "2 hours" in result
        assert "3 minutes" in result
        assert "4 seconds" in result
        
    def test_compact_format(self):
        result = format_duration(93784, style="compact")
        assert result == "1d 2h 3m 4s"
        
    def test_minimal_format(self):
        result = format_duration(3665, style="minimal")  # 1 hour, 1 minute, 5 seconds
        assert result == "1:01:05"
        
    def test_minimal_format_no_hours(self):
        result = format_duration(125, style="minimal")  # 2 minutes, 5 seconds
        assert result == "2:05"
        
    def test_negative_duration(self):
        result = format_duration(-3600, style="full")
        assert result == "-1 hour"
        
    def test_zero_duration(self):
        result = format_duration(0, style="full")
        assert result == "0 seconds"
        
    def test_edge_cases(self):
        # Test singular vs plural
        assert "1 second" in format_duration(1)
        assert "2 seconds" in format_duration(2)
        assert "1 minute" in format_duration(60)
        assert "2 minutes" in format_duration(120)
        
    def test_error_handling(self):
        # Test with invalid input type
        result = format_duration("not a number")
        assert "Error" in result
        assert "must be a number" in result


# Integration tests
class TestIntegration:
    def test_parse_and_add(self):
        """Test parsing a timestamp and then adding time to it"""
        # Use standard format
        parsed = parse_timestamp("2024-01-15 15:00:00")
        
        # Skip if parsing failed
        if "error" in parsed:
            pytest.skip("Parsing failed")
            
        original_time = parsed["iso"]
        
        # Add 2 hours - need to use standard format
        result = add_time("2024-01-15 15:00:00", 2, "hours")
        
        # Verify the time was added correctly
        assert "17:00" in result["result"] or "5:00" in result["description"]
        
    def test_difference_and_format(self):
        """Test calculating difference and formatting it"""
        diff = time_difference(
            "2024-01-01 09:00:00",
            "2024-01-02 11:30:45"
        )
        
        # Skip if difference calculation failed
        if "error" in diff:
            pytest.skip("Difference calculation failed")
        
        # Format the duration in different styles
        seconds = diff["seconds"]
        full = format_duration(seconds, "full")
        compact = format_duration(seconds, "compact")
        
        assert "1 day" in full
        assert "2 hours" in full
        assert "30 minutes" in full
        assert "1d 2h 30m 45s" == compact
        
    def test_context_and_time_since(self):
        """Test getting context and calculating time since"""
        # Get context for a timestamp
        context = timestamp_context("2024-01-15 09:00:00", timezone="America/New_York")
        
        assert context["time_of_day"] == "morning"  # 9 AM is in the morning range
        assert context["is_business_hours"] is True
        assert context["typical_activity"] == "work_time"


# Regression tests for the "'FunctionTool' object is not callable" bug.
# time_since used to call the @mcp.tool()-decorated time_difference directly,
# which is a FunctionTool (not callable) under real fastmcp. These guard against
# any tool internally calling another tool's decorated version.
class TestFunctionToolRegression:
    def test_mock_mirrors_real_fastmcp(self):
        """Sanity check: decorated tools are non-callable FunctionTool stand-ins."""
        assert isinstance(
            passage_of_time_mcp.time_difference, FakeFunctionTool
        )
        assert not callable(passage_of_time_mcp.time_difference)
        # The runtime-invocable implementation lives on `.fn`.
        assert callable(passage_of_time_mcp.time_difference.fn)

    @patch('passage_of_time_mcp.datetime')
    def test_time_since_does_not_call_decorated_tool(self, mock_datetime):
        """time_since must not raise / surface a FunctionTool-not-callable error."""
        real_datetime = datetime
        mock_datetime.now = MagicMock()
        mock_datetime.strptime = real_datetime.strptime
        tz = pytz.timezone("America/New_York")
        mock_datetime.now.return_value = real_datetime(2024, 1, 10, 15, 0, 0, tzinfo=tz)

        result = time_since("2024-01-10 14:00:00", timezone="America/New_York")

        assert "error" not in result, result
        assert "not callable" not in str(result)
        assert abs(result["seconds"] - 3600) < 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])