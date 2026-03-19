"""Incremental data ingestion utilities."""

from .incremental_fetcher import IncrementalFetcher, get_incremental_fetcher

__all__ = ["IncrementalFetcher", "get_incremental_fetcher"]
