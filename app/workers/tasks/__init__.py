"""
Task modules for priority-based routing
"""

from . import critical
from . import high_priority
from . import default_priority
from . import low_priority

__all__ = ['critical', 'high_priority', 'default_priority', 'low_priority']
