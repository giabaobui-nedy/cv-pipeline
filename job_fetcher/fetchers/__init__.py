"""
fetchers — concrete JobFetcher implementations, one module per job board.
"""

from .indeed import IndeedFetcher
from .linkedin import LinkedInFetcher
from .seek import SeekFetcher

__all__ = ["SeekFetcher", "LinkedInFetcher", "IndeedFetcher"]
