from fastmcp import FastMCP
import datetime
import pytz
import os
from typing import Dict, Union, Optional, Literal
from datetime import datetime, timedelta

DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", "America/New_York")

mcp = FastMCP(
    name="Perception of Passage of Time",
    instructions="""You now have access to current_datetime() and can pass along an optional timezone parameter (defaults to NYC). You should call this at the start of every response, so you can get an appreciation for the user's passage of time.

To help you make computations about time, you have multiple other tools:
- time_difference(): Calculate difference between two timestamps
- time_since(): Calculate time elapsed since a timestamp
- parse_timestamp(): Convert timestamp to multiple formats
- add_time(): Add/subtract duration from a timestamp
- timestamp_context(): Get contextual info about a timestamp
- format_duration(): Format seconds into readable text

IMPORTANT: All timestamps must use format "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD" for dates only. 
Examples: "2024-01-15 14:30:00" or "2024-01-15". This ensures no ambiguity in parsing."""
)

def parse_standard_timestamp(timestamp_str: str, timezone: str = DEFAULT_TIMEZONE) -> datetime:
    """
    Parse a timestamp in our standard format.
    Accepts: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    
    Raises ValueError with clear message if format is invalid.
    """
    tz = pytz.timezone(timezone)
    timestamp_str = timestamp_str.strip()
    
    # Try full timestamp format first
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        return tz.localize(dt)
    except ValueError:
        pass
    
    # Try date-only format
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d")
        # For date-only, set time to midnight
        return tz.localize(dt)
    except ValueError:
        pass
    
    # Try with timezone abbreviation
    try:
        # Split off timezone if present
        parts = timestamp_str.rsplit(' ', 2)
        if len(parts) == 3 and len(parts[2]) <= 4:  # Likely a timezone
            dt_str = f"{parts[0]} {parts[1]}"
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            # For now, ignore the provided timezone and use the parameter
            return tz.localize(dt)
    except ValueError:
        pass
    
    # If all parsing attempts failed, raise clear error
    raise ValueError(
        f"Invalid timestamp format: '{timestamp_str}'. "
        f"Expected format: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'. "
        f"Examples: '2024-01-15 14:30:00' or '2024-01-15'"
    )

@mcp.tool()
def current_datetime(timezone: str = DEFAULT_TIMEZONE) -> str:
    """
    Returns the current date and time as a string.
    If you are asked for the current date or time, call this function.
    
    Args:
        timezone: Timezone name (e.g., 'UTC', 'US/Pacific', 'Europe/London').
        Defaults to the environment variable DEFAULT_TIMEZONE (or 'America/New_York' if unset).
    
    Returns:
        A formatted date and time string in format: YYYY-MM-DD HH:MM:SS TZ
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except pytz.exceptions.UnknownTimeZoneError:
        return f"Error: Unknown timezone '{timezone}'. Please use a valid timezone name like 'UTC', 'US/Pacific', or 'Europe/London'."

@mcp.tool()
def time_difference(
    timestamp1: str, 
    timestamp2: str, 
    unit: Literal["auto", "seconds", "minutes", "hours", "days"] = "auto",
    timezone: str = DEFAULT_TIMEZONE
) -> Dict[str, Union[int, float, str, bool]]:
    """
    Calculate the time difference between two timestamps.
    
    Timestamps must be in format: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    
    Args:
        timestamp1: First timestamp (earlier time expected)
        timestamp2: Second timestamp (later time expected)
        unit: Desired unit for the result. "auto" provides multiple formats
        timezone: Timezone for parsing ambiguous timestamps
    
    Returns:
        Dictionary containing:
        - seconds: Total difference in seconds
        - formatted: Human-readable format (e.g., "3 hours, 10 minutes")
        - requested_unit: Difference in the requested unit (if not "auto")
        - is_negative: Boolean indicating if timestamp1 > timestamp2
    """
    try:
        dt1 = parse_standard_timestamp(timestamp1, timezone)
        dt2 = parse_standard_timestamp(timestamp2, timezone)
        
        # Calculate difference
        delta = dt2 - dt1
        total_seconds = delta.total_seconds()
        is_negative = total_seconds < 0
        abs_seconds = abs(total_seconds)
        
        # Format human-readable string
        def format_timedelta(seconds):
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if secs > 0 or not parts:
                parts.append(f"{secs} second{'s' if secs != 1 else ''}")
            
            return ", ".join(parts)
        
        formatted = format_timedelta(abs_seconds)
        if is_negative:
            formatted = f"-{formatted}"
        
        result = {
            "seconds": total_seconds,
            "formatted": formatted,
            "is_negative": is_negative
        }
        
        # Add requested unit if not "auto"
        if unit != "auto":
            unit_conversions = {
                "seconds": 1,
                "minutes": 60,
                "hours": 3600,
                "days": 86400
            }
            result["requested_unit"] = total_seconds / unit_conversions[unit]
        
        return result
        
    except ValueError as e:
        return {
            "error": str(e),
            "seconds": 0,
            "formatted": "Error parsing timestamps",
            "is_negative": False
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "seconds": 0,
            "formatted": "Error parsing timestamps",
            "is_negative": False
        }

@mcp.tool()
def time_since(
    timestamp: str,
    timezone: str = DEFAULT_TIMEZONE
) -> Dict[str, Union[int, float, str]]:
    """
    Calculate time elapsed since a given timestamp until now.
    
    Timestamp must be in format: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    
    Args:
        timestamp: Past timestamp to compare against current time
        timezone: Timezone for parsing and current time
    
    Returns:
        Dictionary containing:
        - seconds: Seconds elapsed (negative if timestamp is in future)
        - formatted: Human-readable format (e.g., "2 days, 3 hours ago")
        - context: Contextual description (e.g., "earlier today", "yesterday")
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Use time_difference to calculate
        diff = time_difference(timestamp, now_str, unit="auto", timezone=timezone)
        
        # Check if time_difference returned an error
        if "error" in diff:
            return {
                "error": diff.get("error", "Unknown error in time_difference"),
                "seconds": 0,
                "formatted": "Error calculating time since",
                "context": "unknown"
            }
        
        seconds = diff["seconds"]
        abs_seconds = abs(seconds)
        
        # Generate contextual description
        dt = parse_standard_timestamp(timestamp, timezone)
        
        context = ""
        if seconds < 0:
            context = "in the future"
        elif abs_seconds < 60:
            context = "just now"
        elif abs_seconds < 3600:
            context = "earlier"
        elif abs_seconds < 86400:
            if dt.date() == now.date():
                context = "earlier today"
            else:
                context = "yesterday"
        elif abs_seconds < 172800:  # 2 days
            context = "yesterday"
        elif abs_seconds < 604800:  # 1 week
            context = "this week"
        elif abs_seconds < 2592000:  # 30 days
            context = "this month"
        else:
            context = "a while ago"
        
        formatted = diff["formatted"] + (" ago" if seconds >= 0 else " from now")
        
        return {
            "seconds": seconds,
            "formatted": formatted,
            "context": context
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "seconds": 0,
            "formatted": "Error calculating time since",
            "context": "unknown"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "seconds": 0,
            "formatted": "Error calculating time since",
            "context": "unknown"
        }

@mcp.tool()
def parse_timestamp(
    timestamp: str,
    source_timezone: Optional[str] = None,
    target_timezone: str = DEFAULT_TIMEZONE
) -> Dict[str, str]:
    """
    Parse and convert a timestamp to multiple formats.
    
    Timestamp must be in format: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    
    Args:
        timestamp: Timestamp string in standard format
        source_timezone: Timezone of the input (if None, uses target_timezone)
        target_timezone: Desired output timezone
    
    Returns:
        Dictionary containing:
        - iso: ISO 8601 format
        - unix: Unix timestamp (seconds since epoch)
        - human: Human-friendly format
        - timezone: Timezone name
        - day_of_week: Full day name
        - date: Date only (YYYY-MM-DD)
        - time: Time only (HH:MM:SS)
    """
    try:
        # Parse the timestamp
        parse_tz = source_timezone or target_timezone
        dt = parse_standard_timestamp(timestamp, parse_tz)
        
        # Convert to target timezone if different
        if source_timezone and source_timezone != target_timezone:
            tgt_tz = pytz.timezone(target_timezone)
            dt = dt.astimezone(tgt_tz)
        
        return {
            "iso": dt.isoformat(),
            "unix": str(int(dt.timestamp())),
            "human": dt.strftime("%B %d, %Y at %I:%M %p %Z"),
            "timezone": target_timezone,
            "day_of_week": dt.strftime("%A"),
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M:%S")
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "iso": "",
            "unix": "",
            "human": "Error parsing timestamp",
            "timezone": target_timezone,
            "day_of_week": "",
            "date": "",
            "time": ""
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "iso": "",
            "unix": "",
            "human": "Error parsing timestamp",
            "timezone": target_timezone,
            "day_of_week": "",
            "date": "",
            "time": ""
        }

@mcp.tool()
def add_time(
    timestamp: str,
    duration: Union[int, float],
    unit: Literal["seconds", "minutes", "hours", "days", "weeks"],
    timezone: str = DEFAULT_TIMEZONE
) -> Dict[str, str]:
    """
    Add a duration to a timestamp.
    
    Timestamp must be in format: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    
    Args:
        timestamp: Starting timestamp in standard format
        duration: Amount to add (can be negative to subtract)
        unit: Unit of the duration
        timezone: Timezone for calculations
    
    Returns:
        Dictionary containing:
        - result: Resulting timestamp in same format as input
        - iso: ISO 8601 format of result
        - description: Natural language description (e.g., "tomorrow at 3:00 PM")
    """
    try:
        tz = pytz.timezone(timezone)
        dt = parse_standard_timestamp(timestamp, timezone)
        
        # Remember if input was date-only
        is_date_only = ":" not in timestamp
        
        # Calculate timedelta based on unit
        if unit == "seconds":
            delta = timedelta(seconds=duration)
        elif unit == "minutes":
            delta = timedelta(minutes=duration)
        elif unit == "hours":
            delta = timedelta(hours=duration)
        elif unit == "days":
            delta = timedelta(days=duration)
        elif unit == "weeks":
            delta = timedelta(weeks=duration)
        else:
            raise ValueError(f"Invalid unit: {unit}")
        
        # Add duration
        result_dt = dt + delta
        
        # Generate natural language description
        now = datetime.now(tz)
        days_diff = (result_dt.date() - now.date()).days
        
        if days_diff == 0:
            day_desc = "today"
        elif days_diff == 1:
            day_desc = "tomorrow"
        elif days_diff == -1:
            day_desc = "yesterday"
        elif days_diff > 1 and days_diff <= 7:
            day_desc = f"next {result_dt.strftime('%A')}"
        elif days_diff < -1 and days_diff >= -7:
            day_desc = f"last {result_dt.strftime('%A')}"
        else:
            day_desc = result_dt.strftime("%B %d, %Y")
        
        time_desc = result_dt.strftime("%I:%M %p").lstrip("0")
        description = f"{day_desc} at {time_desc}" if not is_date_only else day_desc
        
        # Format result to match input format
        if is_date_only:
            result_str = result_dt.strftime("%Y-%m-%d")
        else:
            result_str = result_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "result": result_str,
            "iso": result_dt.isoformat(),
            "description": description
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "result": "Error adding time",
            "iso": "",
            "description": "Error calculating result"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "result": "Error adding time",
            "iso": "",
            "description": "Error calculating result"
        }

@mcp.tool()
def timestamp_context(
    timestamp: str,
    timezone: str = DEFAULT_TIMEZONE
) -> Dict[str, Union[str, bool, int]]:
    """
    Provide contextual information about a timestamp.
    
    Timestamp must be in format: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    
    Args:
        timestamp: Timestamp to analyze in standard format
        timezone: Timezone for context
    
    Returns:
        Dictionary containing:
        - time_of_day: "early_morning", "morning", "afternoon", "evening", "late_night"
        - day_of_week: Full day name
        - is_weekend: Boolean
        - is_business_hours: Boolean (Mon-Fri 9-5)
        - hour_24: Hour in 24-hour format
        - typical_activity: Contextual description (e.g., "lunch_time", "commute_time")
        - relative_day: "today", "yesterday", "tomorrow", or None
    """
    try:
        tz = pytz.timezone(timezone)
        dt = parse_standard_timestamp(timestamp, timezone)
        now = datetime.now(tz)
        
        hour = dt.hour
        
        # Determine time of day
        if 5 <= hour < 9:
            time_of_day = "early_morning"
        elif 9 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "late_night"
        
        # Day of week and weekend check
        day_of_week = dt.strftime("%A")
        is_weekend = dt.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        # Business hours check (Mon-Fri 9-5)
        is_business_hours = (
            not is_weekend and 
            9 <= hour < 17
        )
        
        # Typical activity based on time
        if 6 <= hour < 9:
            typical_activity = "commute_time"
        elif 12 <= hour < 13:
            typical_activity = "lunch_time"
        elif 17 <= hour < 19:
            typical_activity = "commute_time"
        elif 19 <= hour < 21:
            typical_activity = "dinner_time"
        elif 22 <= hour or hour < 6:
            typical_activity = "sleeping_time"
        else:
            typical_activity = "work_time" if is_business_hours else "leisure_time"
        
        # Relative day
        days_diff = (dt.date() - now.date()).days
        if days_diff == 0:
            relative_day = "today"
        elif days_diff == -1:
            relative_day = "yesterday"
        elif days_diff == 1:
            relative_day = "tomorrow"
        else:
            relative_day = None
        
        return {
            "time_of_day": time_of_day,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "is_business_hours": is_business_hours,
            "hour_24": hour,
            "typical_activity": typical_activity,
            "relative_day": relative_day
        }
        
    except ValueError as e:
        return {
            "error": str(e),
            "time_of_day": "unknown",
            "day_of_week": "",
            "is_weekend": False,
            "is_business_hours": False,
            "hour_24": 0,
            "typical_activity": "unknown",
            "relative_day": None
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "time_of_day": "unknown",
            "day_of_week": "",
            "is_weekend": False,
            "is_business_hours": False,
            "hour_24": 0,
            "typical_activity": "unknown",
            "relative_day": None
        }

@mcp.tool()
def format_duration(
    seconds: Union[int, float],
    style: Literal["full", "compact", "minimal"] = "full"
) -> str:
    """
    Format a duration in seconds into human-readable text.
    
    Args:
        seconds: Duration in seconds (can be negative)
        style: Format style
            - "full": "2 hours, 30 minutes, 15 seconds"
            - "compact": "2h 30m 15s"
            - "minimal": "2:30:15"
    
    Returns:
        Formatted duration string
    """
    try:
        # Validate input
        seconds = float(seconds)
        
        # Handle negative durations
        is_negative = seconds < 0
        abs_seconds = abs(seconds)
        
        # Break down into components
        days = int(abs_seconds // 86400)
        hours = int((abs_seconds % 86400) // 3600)
        minutes = int((abs_seconds % 3600) // 60)
        secs = int(abs_seconds % 60)
        
        if style == "full":
            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if secs > 0 or not parts:
                parts.append(f"{secs} second{'s' if secs != 1 else ''}")
            result = ", ".join(parts)
            
        elif style == "compact":
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            if minutes > 0:
                parts.append(f"{minutes}m")
            if secs > 0 or not parts:
                parts.append(f"{secs}s")
            result = " ".join(parts)
            
        elif style == "minimal":
            if days > 0:
                result = f"{days}:{hours:02d}:{minutes:02d}:{secs:02d}"
            elif hours > 0:
                result = f"{hours}:{minutes:02d}:{secs:02d}"
            else:
                result = f"{minutes}:{secs:02d}"
        else:
            raise ValueError(f"Invalid style: {style}. Must be 'full', 'compact', or 'minimal'")
        
        return f"-{result}" if is_negative else result
        
    except (ValueError, TypeError) as e:
        return f"Error: Invalid input. Seconds must be a number. {str(e)}"
    except Exception as e:
        return f"Error formatting duration: {str(e)}"

from starlette.requests import Request
from starlette.responses import PlainTextResponse

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> PlainTextResponse:
    # Hosting health checks need a route that *completes*: /sse streams
    # forever, so a checker pointed at it reads as a timeout even while the
    # server is healthy (this silently killed the June 2025 Render deploys).
    return PlainTextResponse("OK")

if __name__ == "__main__":
    import uvicorn
    from contextlib import asynccontextmanager
    from starlette.applications import Starlette

    port = int(os.environ.get("PORT", 8000))

    # Serve BOTH MCP transports during the migration era: SSE is deprecated
    # upstream but every existing connector was configured against /sse, so
    # it must keep working while new clients point at streamable HTTP.
    #   /mcp            — streamable HTTP (modern; use for new connectors)
    #   /sse, /messages — legacy SSE (existing connectors keep working)
    http_app = mcp.http_app(transport="streamable-http", path="/mcp")
    sse_app = mcp.http_app(transport="sse", path="/sse")

    @asynccontextmanager
    async def dual_lifespan(app):
        # Both sub-apps need their lifespans run (the streamable session
        # manager in particular refuses requests without it).
        async with http_app.lifespan(app):
            async with sse_app.lifespan(app):
                yield

    app = Starlette(
        routes=[*http_app.routes, *sse_app.routes],
        lifespan=dual_lifespan,
    )

    class PathNormalizer:
        # The streamable mount answers at /mcp/ and 307-redirects bare
        # /mcp; not every MCP client follows redirects, so rewrite the
        # path in-process and serve both spellings directly.
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope.get("type") == "http" and scope.get("path") == "/mcp":
                scope = dict(scope, path="/mcp/", raw_path=b"/mcp/")
            await self.app(scope, receive, send)

    uvicorn.run(PathNormalizer(app), host="0.0.0.0", port=port)