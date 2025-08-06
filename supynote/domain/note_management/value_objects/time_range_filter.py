"""Time range filter value object."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from ...shared.base_value_object import ValueObject


class TimeRange(Enum):
    """Supported time range options."""
    WEEK = "week"
    TWO_WEEKS = "2weeks"
    MONTH = "month"
    ALL = "all"


class TimeRangeFilter(ValueObject):
    """Represents a time-based filter for notes."""
    
    def __init__(self, time_range: TimeRange):
        self._time_range = time_range
        self._reference_date = datetime.now()
    
    @classmethod
    def from_string(cls, range_str: str) -> 'TimeRangeFilter':
        """Create from a string like 'week', '2weeks', 'month', 'all'."""
        try:
            time_range = TimeRange(range_str)
        except ValueError:
            # Default to ALL if invalid
            time_range = TimeRange.ALL
        return cls(time_range)
    
    @property
    def value(self) -> TimeRange:
        """Get the time range value."""
        return self._time_range
    
    @property
    def cutoff_date(self) -> Optional[datetime]:
        """Get the cutoff date for filtering."""
        if self._time_range == TimeRange.ALL:
            return None
        elif self._time_range == TimeRange.WEEK:
            return self._reference_date - timedelta(days=7)
        elif self._time_range == TimeRange.TWO_WEEKS:
            return self._reference_date - timedelta(days=14)
        elif self._time_range == TimeRange.MONTH:
            return self._reference_date - timedelta(days=30)
        else:
            return None
    
    def includes_date(self, date: datetime) -> bool:
        """Check if a given date is included in this filter."""
        cutoff = self.cutoff_date
        if cutoff is None:
            return True
        return date >= cutoff
    
    def is_all_time(self) -> bool:
        """Check if this filter includes all time."""
        return self._time_range == TimeRange.ALL
    
    def __eq__(self, other: object) -> bool:
        """Filters are equal if they have the same range."""
        if not isinstance(other, TimeRangeFilter):
            return False
        return self._time_range == other._time_range
    
    def __hash__(self) -> int:
        """Hash based on time range."""
        return hash(self._time_range)
    
    def __str__(self) -> str:
        """String representation."""
        return self._time_range.value
    
    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"TimeRangeFilter({self._time_range.value})"