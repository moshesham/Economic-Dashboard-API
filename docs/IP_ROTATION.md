# IP Rotation Guide

Consolidated guidance for IP rotation strategies and implementation.

## Why IP Rotation?
- Avoid rate-limit bans
- Distribute requests across IPs
- Improve reliability for scraping/ingestion

## Approaches
- Residential proxy providers
- Rotating proxy pools
- Backoff + jitter strategy in HTTP clients

## Implementation Hooks
- `modules/http_client.py`: pluggable proxy settings per source
- Configure per-client via environment variables

## Operational Notes
- Monitor failure codes and switch pools on thresholds
- Log proxy performance and error distribution
