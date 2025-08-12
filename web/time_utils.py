"""
Unified time handling utilities for newsletter generator web application

This module provides consistent timezone-aware datetime handling across the application:
- All database storage in UTC
- All API responses in ISO 8601 UTC format  
- Consistent timezone conversions
- User timezone detection and handling
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union

# Try to import pytz, fallback to standard library if not available
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    # Create a simple timezone class for KST as fallback
    class _SimpleTimezone:
        @staticmethod
        def timezone(name: str):
            if name == 'Asia/Seoul':
                # KST is UTC+9
                return timezone(timedelta(hours=9))
            return timezone.utc
    pytz = _SimpleTimezone


def get_utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime object
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def get_kst_now() -> datetime:
    """Get current Korea Standard Time as timezone-aware datetime object
    
    Returns:
        datetime: Current KST time with timezone info
    """
    kst_tz = pytz.timezone('Asia/Seoul')
    return datetime.now(kst_tz)


def to_utc(dt: Union[datetime, str]) -> datetime:
    """Convert datetime to UTC timezone-aware datetime
    
    Args:
        dt: datetime object or ISO string to convert
        
    Returns:
        datetime: UTC timezone-aware datetime
    """
    if isinstance(dt, str):
        # Parse ISO string
        if dt.endswith('Z'):
            # Already UTC
            return datetime.fromisoformat(dt[:-1]).replace(tzinfo=timezone.utc)
        else:
            # Try to parse with timezone info
            try:
                return datetime.fromisoformat(dt)
            except ValueError:
                # Assume naive datetime is UTC
                return datetime.fromisoformat(dt).replace(tzinfo=timezone.utc)
    
    if dt.tzinfo is None:
        # Naive datetime, assume UTC
        return dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC
    return dt.astimezone(timezone.utc)


def to_kst(dt: Union[datetime, str]) -> datetime:
    """Convert datetime to Korea Standard Time timezone-aware datetime
    
    Args:
        dt: datetime object or ISO string to convert
        
    Returns:
        datetime: KST timezone-aware datetime
    """
    kst_tz = pytz.timezone('Asia/Seoul')
    
    if isinstance(dt, str):
        dt = to_utc(dt)  # First convert to UTC
    
    if dt.tzinfo is None:
        # Naive datetime, assume UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(kst_tz)


def to_iso_utc(dt: Union[datetime, str]) -> str:
    """Convert datetime to ISO 8601 UTC string format
    
    Args:
        dt: datetime object or string to convert
        
    Returns:
        str: ISO 8601 UTC string (YYYY-MM-DDTHH:MM:SS.fffffZ)
    """
    utc_dt = to_utc(dt)
    return utc_dt.isoformat().replace('+00:00', 'Z')


def to_iso_kst(dt: Union[datetime, str]) -> str:
    """Convert datetime to ISO 8601 KST string format
    
    Args:
        dt: datetime object or string to convert
        
    Returns:
        str: ISO 8601 KST string with timezone info
    """
    kst_dt = to_kst(dt)
    return kst_dt.isoformat()


def format_display_time(dt: Union[datetime, str], user_timezone: Optional[str] = None) -> dict:
    """Format datetime for frontend display with multiple timezone options
    
    Args:
        dt: datetime object or ISO string
        user_timezone: Optional user timezone (e.g., 'America/New_York')
        
    Returns:
        dict: Dictionary with various time formats for display
        {
            'utc_iso': '2025-08-11T07:30:00.000Z',
            'kst_iso': '2025-08-11T16:30:00.000+09:00', 
            'kst_display': '2025-08-11 16:30:00 KST',
            'user_iso': '2025-08-11T03:30:00.000-04:00',  # if user_timezone provided
            'user_display': '2025-08-11 03:30:00 EDT',  # if user_timezone provided
            'timestamp': 1723356600  # Unix timestamp for JS
        }
    """
    utc_dt = to_utc(dt)
    kst_dt = to_kst(dt)
    
    result = {
        'utc_iso': to_iso_utc(utc_dt),
        'kst_iso': to_iso_kst(utc_dt),
        'kst_display': kst_dt.strftime('%Y-%m-%d %H:%M:%S KST'),
        'timestamp': int(utc_dt.timestamp())
    }
    
    # Add user timezone if provided
    if user_timezone:
        try:
            user_tz = pytz.timezone(user_timezone)
            user_dt = utc_dt.astimezone(user_tz)
            result['user_iso'] = user_dt.isoformat()
            result['user_display'] = user_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        except Exception:  # Handle both pytz.exceptions.UnknownTimeZoneError and other errors
            # Invalid timezone or pytz not available, skip user timezone
            pass
    
    return result


def parse_sqlite_timestamp(timestamp_str: str) -> datetime:
    """Parse SQLite CURRENT_TIMESTAMP string to timezone-aware UTC datetime
    
    SQLite CURRENT_TIMESTAMP returns UTC time in various formats:
    - '2025-08-11 07:30:00'
    - '2025-08-11 07:30:00.123'
    - '2025-08-11T07:30:00.123456Z' (ISO format from our time_utils)
    
    Args:
        timestamp_str: SQLite timestamp string
        
    Returns:
        datetime: UTC timezone-aware datetime
    """
    # SQLite CURRENT_TIMESTAMP is always UTC
    try:
        # Try multiple parsing strategies in order of likelihood
        
        # 1. ISO format with Z suffix (our generated timestamps)
        if timestamp_str.endswith('Z'):
            return datetime.fromisoformat(timestamp_str[:-1]).replace(tzinfo=timezone.utc)
        
        # 2. ISO format without Z
        if 'T' in timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str)
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            except ValueError:
                pass
        
        # 3. SQLite format with microseconds (2025-08-11 07:30:00.123456)
        if '.' in timestamp_str:
            try:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        
        # 4. SQLite format without microseconds (2025-08-11 07:30:00)
        try:
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        
        # 5. Final fallback: try fromisoformat
        dt = datetime.fromisoformat(timestamp_str)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        
    except ValueError as e:
        print(f"[WARNING] Failed to parse timestamp '{timestamp_str}': {e}")
        # Last resort: use current time
        return get_utc_now()


def get_timezone_info() -> dict:
    """Get comprehensive timezone information for the application
    
    Returns:
        dict: Timezone information for client synchronization
    """
    now_utc = get_utc_now()
    now_kst = get_kst_now()
    
    return {
        'server_timezone': 'Asia/Seoul',
        'utc_time': to_iso_utc(now_utc),
        'kst_time': to_iso_kst(now_utc),
        'kst_display': now_kst.strftime('%Y-%m-%d %H:%M:%S KST'),
        'utc_timestamp': int(now_utc.timestamp()),
        'kst_offset': '+09:00',
        'supported_timezones': [
            'UTC',
            'Asia/Seoul'
        ] + (['America/New_York', 'America/Los_Angeles', 'Europe/London', 'Europe/Berlin', 'Asia/Tokyo'] if PYTZ_AVAILABLE else [])
    }


# Deprecated function names for backward compatibility
def utc_now():
    """Deprecated: Use get_utc_now() instead"""
    return get_utc_now()


def kst_now():
    """Deprecated: Use get_kst_now() instead"""  
    return get_kst_now()