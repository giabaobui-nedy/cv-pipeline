"""
job_fetcher — strategy-pattern job description fetcher for the CV pipeline.

Quickstart
----------
>>> from job_fetcher import JobFetcherRouter, is_visa_friendly
>>> router = JobFetcherRouter()
>>> listing = router.fetch("https://www.seek.com.au/job/12345678")
>>> print(listing.title, listing.company)
>>> if is_visa_friendly(listing):
...     print("Worth applying!")
"""

from .models import JobFetchError, JobListing, JobStub
from .router import JobFetcherRouter
from .visa_filter import detect_visa_signals, is_visa_friendly

__all__ = [
    "JobListing",
    "JobStub",
    "JobFetchError",
    "JobFetcherRouter",
    "detect_visa_signals",
    "is_visa_friendly",
]
