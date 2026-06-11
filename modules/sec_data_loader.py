"""
SEC Data Loading Module for Economic Dashboard.
Optimized OOP-first design with absolute minimum redundancy, in-memory caching,
and full fallback compatibility for legacy scripts.
"""

import os
import io
import json
import zipfile
import requests
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Iterable
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

# Check Streamlit environment safely
try:
    import streamlit as st
except ImportError:
    st = None

# Import database functions (backend selected by modules.database.factory)
try:
    from modules.database import get_db_connection
    DB_BACKEND_AVAILABLE = True
except ImportError:
    DB_BACKEND_AVAILABLE = False


class SECDataLoader:
    """
    Unified client class for accessing SEC EDGAR databases.
    Implements local caching, rate limiting, and fallback lookup patterns.
    """

    SEC_BASE_URL = "https://www.sec.gov"
    SEC_DATA_URL = "https://data.sec.gov"
    SEC_FSDS_URL = f"{SEC_BASE_URL}/files/dera/data/financial-statement-data-sets"
    SEC_FTD_URL = f"{SEC_BASE_URL}/data/foiadocsfailsdocs"
    SEC_BULK_COMPANYFACTS_URL = f"{SEC_BASE_URL}/Archives/edgar/daily-index/xbrl/companyfacts.zip"
    SEC_BULK_SUBMISSIONS_URL = f"{SEC_BASE_URL}/Archives/edgar/daily-index/bulkdata/submissions.zip"
    SEC_COMPANY_TICKERS_URL = f"{SEC_BASE_URL}/files/company_tickers.json"

    BULK_REFRESH_DAYS = 7
    REQUEST_DELAY = 0.1  # Enforce max 10 requests per second

    BULK_DATASETS = {
        "companyfacts": {
            "url": SEC_BULK_COMPANYFACTS_URL,
            "archive_name": "companyfacts.zip",
            "member_names": lambda cik: [f"companyfacts/CIK{cik}.json", f"CIK{cik}.json"],
        },
        "submissions": {
            "url": SEC_BULK_SUBMISSIONS_URL,
            "archive_name": "submissions.zip",
            "member_names": lambda cik: [f"submissions/CIK{cik}.json", f"CIK{cik}.json"],
        },
    }

    def __init__(self, user_agent: Optional[str] = None, cache_dir: Optional[Path] = None):
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT") or "Economic-Dashboard/1.0 (contact@example.com)"

        # In-memory performance caches
        self._tickers_df_cache: Optional[pd.DataFrame] = None
        self._cik_by_ticker_cache: Dict[str, str] = {}

        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent.parent / "data" / "cache" / "sec"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_headers_for_url(self, url: str) -> Dict[str, str]:
        """Dynamically builds Host header according to target domain requirements."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }
        if "data.sec.gov" in url:
            headers["Host"] = "data.sec.gov"
        elif "www.sec.gov" in url:
            headers["Host"] = "www.sec.gov"
        return headers

    def _notify(self, message: str, level: str = "warning"):
        """Centralized warning and error message dispatcher."""
        if level == "error":
            logger.error(message)
        else:
            logger.warning(message)

        if st is not None:
            try:
                if level == "error":
                    st.error(message)
                else:
                    st.warning(message)
            except Exception:
                pass

    def _check_db_available(self) -> bool:
        """Internal helper to ensure db connection is present."""
        if not DB_BACKEND_AVAILABLE:
            self._notify("Database backend connection is not configured or available.")
            return False
        return True

    def _is_stale(self, path: Path, max_age_days: int) -> bool:
        """Determines if a cached file requires updating."""
        if not path.exists():
            return True
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        return age >= timedelta(days=max_age_days)

    def _download_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Downloads SEC endpoints with exponential backoff, rate limiting, and error diagnostic helpers."""
        headers = self._get_headers_for_url(url)

        for attempt in range(max_retries):
            try:
                time.sleep(self.REQUEST_DELAY)
                response = requests.get(url, headers=headers, timeout=60)

                if response.status_code == 200:
                    return response
                if response.status_code == 403:
                    self._notify("SEC returned 403 Forbidden. Validate your User-Agent format: 'Name (email)'.", "error")
                    return None
                if response.status_code == 404:
                    return None
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                else:
                    response.raise_for_status()

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    self._notify(f"SEC download error: {e}", "error")
                    raise e
                time.sleep(2 ** attempt)
        return None

    def _write_response_to_cache(self, url: str, destination: Path) -> Optional[Path]:
        """Downloads a URL and writes its raw payload directly to disk."""
        response = self._download_with_retry(url)
        if response is None:
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)
        return destination

    def _ensure_cached_reference_file(
        self,
        cache_name: str,
        url: str,
        max_age_days: int = BULK_REFRESH_DAYS,
        force: bool = False,
    ) -> Optional[Path]:
        """Caches structural configuration files locally."""
        cache_path = self.cache_dir / cache_name
        if force or self._is_stale(cache_path, max_age_days):
            return self._write_response_to_cache(url, cache_path)
        return cache_path

    def _load_json_file(self, path: Path) -> Dict[str, Any]:
        """Safely loads text files containing JSON structures."""
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except Exception as exc:
            self._notify(f"Failed to parse cached SEC file {path.name}: {exc}")
            return {}

    # =============================================================================
    # Bulk ZIP Dataset Engine (Ad-hoc)
    # =============================================================================

    def download_bulk_archive(self, dataset: str, force: bool = False) -> Optional[Path]:
        """Ad-hoc download execution for nightly ZIP bulk datasets."""
        if dataset not in self.BULK_DATASETS:
            raise ValueError(f"Unknown bulk dataset: {dataset}")
        config = self.BULK_DATASETS[dataset]
        return self._ensure_cached_reference_file(
            cache_name=config["archive_name"],
            url=config["url"],
            force=force,
        )

    def _extract_bulk_company_json(self, dataset: str, cik: str, force: bool = False) -> Optional[Path]:
        """Extracts CIK metadata directly from downloaded bulk datasets."""
        cik_padded = str(cik).zfill(10)
        archive_path = self.download_bulk_archive(dataset, force=force)
        if archive_path is None:
            return None

        extracted_dir = self.cache_dir / dataset
        extracted_dir.mkdir(parents=True, exist_ok=True)
        extracted_path = extracted_dir / f"CIK{cik_padded}.json"

        if extracted_path.exists() and extracted_path.stat().st_mtime >= archive_path.stat().st_mtime:
            return extracted_path

        member_names: Iterable[str] = self.BULK_DATASETS[dataset]["member_names"](cik_padded)
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                payload = None
                for member_name in member_names:
                    try:
                        payload = archive.read(member_name)
                        break
                    except KeyError:
                        continue
                if payload is None:
                    return None
                extracted_path.write_bytes(payload)
                return extracted_path
        except Exception as exc:
            self._notify(f"Could not extract {dataset} mapping for CIK {cik_padded}: {exc}")
            return None

    def _load_bulk_company_json(self, dataset: str, cik: str, force: bool = False) -> Dict[str, Any]:
        """Directly loads extracted JSON payloads from bulk archives."""
        extracted_path = self._extract_bulk_company_json(dataset, cik, force=force)
        return self._load_json_file(extracted_path) if extracted_path else {}

    # =============================================================================
    # Resolvers (CIK / Tickers)
    # =============================================================================

    def get_company_tickers_df(self, force: bool = False) -> pd.DataFrame:
        """Parses the primary company mapping from the SEC index."""
        if self._tickers_df_cache is not None and not force:
            return self._tickers_df_cache

        cache_path = self._ensure_cached_reference_file(
            cache_name="company_tickers.json",
            url=self.SEC_COMPANY_TICKERS_URL,
            force=force,
        )
        if cache_path is None:
            return pd.DataFrame()

        data = self._load_json_file(cache_path)
        if not data:
            return pd.DataFrame()

        try:
            df = pd.DataFrame(data.values())
            if df.empty:
                return df

            df = df.rename(columns={"cik_str": "cik"})
            for col in ["cik", "ticker", "title"]:
                if col not in df.columns:
                    df[col] = None

            df = df[["cik", "ticker", "title"]]
            df["cik"] = df["cik"].astype(str).str.zfill(10)
            df["ticker"] = df["ticker"].astype(str).str.upper()

            # Cache references to optimize sequential lookup requests
            self._tickers_df_cache = df
            self._cik_by_ticker_cache = df.set_index("ticker")["cik"].to_dict()
            return df
        except Exception as exc:
            self._notify(f"Could not parse cached SEC tickers: {exc}")
            return pd.DataFrame()

    def lookup_cik(self, ticker: str) -> Optional[str]:
        """Resolves stock tickers to 10-digit CIK strings via in-memory O(1) indexes."""
        ticker_upper = ticker.upper()
        if ticker_upper in self._cik_by_ticker_cache:
            return self._cik_by_ticker_cache[ticker_upper]

        self.get_company_tickers_df()
        return self._cik_by_ticker_cache.get(ticker_upper)

    # =============================================================================
    # Dual-Mode Fetching Engines (API Ticker & CIK-based vs. Bulk Dataset Inputs)
    # =============================================================================

    def get_company_facts(self, cik_or_ticker: str, use_bulk: bool = False, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetches XBRL company facts from nightly bulk zip structures or live real-time JSON APIs."""
        cik = self.lookup_cik(cik_or_ticker) if not cik_or_ticker.isdigit() else cik_or_ticker
        if not cik:
            self._notify(f"Could not resolve CIK/Ticker: {cik_or_ticker}")
            return {}

        cik_padded = str(cik).zfill(10)
        if use_bulk:
            return self._load_bulk_company_json("companyfacts", cik_padded, force=force_refresh)

        # Direct Web REST API Lookup
        live_endpoint = f"{self.SEC_DATA_URL}/api/xbrl/companyfacts/CIK{cik_padded}.json"
        cache_path = self.cache_dir / "companyfacts" / f"CIK{cik_padded}.json"

        if force_refresh or self._is_stale(cache_path, self.BULK_REFRESH_DAYS):
            self._write_response_to_cache(live_endpoint, cache_path)
        return self._load_json_file(cache_path)

    def get_company_submissions(self, cik_or_ticker: str, use_bulk: bool = False, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetches company submission records from bulk indexes or real-time endpoints."""
        cik = self.lookup_cik(cik_or_ticker) if not cik_or_ticker.isdigit() else cik_or_ticker
        if not cik:
            self._notify(f"Could not resolve CIK/Ticker: {cik_or_ticker}")
            return {}

        cik_padded = str(cik).zfill(10)
        if use_bulk:
            return self._load_bulk_company_json("submissions", cik_padded, force=force_refresh)

        # Direct Web REST API Lookup
        live_endpoint = f"{self.SEC_DATA_URL}/submissions/CIK{cik_padded}.json"
        cache_path = self.cache_dir / "submissions" / f"CIK{cik_padded}.json"

        if force_refresh or self._is_stale(cache_path, self.BULK_REFRESH_DAYS):
            self._write_response_to_cache(live_endpoint, cache_path)
        return self._load_json_file(cache_path)

    def get_xbrl_frame(self, concept: str, unit: str, period: str, taxonomy: str = "us-gaap") -> Dict[str, Any]:
        """Fetches specific frames matching calendar and taxonomy specifications."""
        endpoint = f"{self.SEC_DATA_URL}/api/xbrl/frames/{taxonomy}/{concept}/{unit}/{period}.json"
        cache_path = self.cache_dir / "frames" / f"frames_{taxonomy}_{concept}_{unit}_{period}.json"

        if self._is_stale(cache_path, max_age_days=1):
            self._write_response_to_cache(endpoint, cache_path)
        return self._load_json_file(cache_path)

    # =============================================================================
    # Parsers & Processing Layouts
    # =============================================================================

    def company_facts_to_dataframe(self, company_facts: Dict[str, Any], concepts: Optional[Iterable[str]] = None) -> pd.DataFrame:
        """Processes structured XBRL JSON formats into normalized Pandas shapes."""
        concepts_filter = set(concepts) if concepts else None
        facts = company_facts.get("facts", {})
        cik = str(company_facts.get("cik", "")).zfill(10)

        rows: List[Dict[str, Any]] = []
        for taxonomy_facts in facts.values():
            for concept, concept_data in taxonomy_facts.items():
                if concepts_filter and concept not in concepts_filter:
                    continue

                for unit, values in concept_data.get("units", {}).items():
                    for value in values:
                        end_date = pd.to_datetime(value.get("end"), errors="coerce")
                        if pd.isna(end_date):
                            continue

                        rows.append(
                            {
                                "cik": cik,
                                "concept": concept,
                                "unit": unit,
                                "value": value.get("val"),
                                "start_date": pd.to_datetime(value.get("start"), errors="coerce"),
                                "end_date": end_date,
                                "fy": value.get("fy"),
                                "fp": value.get("fp"),
                                "form": value.get("form"),
                                "filed": pd.to_datetime(value.get("filed"), errors="coerce"),
                                "accn": value.get("accn"),
                            }
                        )
        return pd.DataFrame(rows)

    def extract_financial_metric(self, company_facts: Dict[str, Any], concept: str, taxonomy: str = "us-gaap") -> pd.DataFrame:
        """Leverages unified parser engine to isolate specific concepts and format legacy schemas."""
        df = self.company_facts_to_dataframe(company_facts, concepts=[concept])
        if df.empty:
            return pd.DataFrame()

        df = df.rename(columns={"fy": "fiscal_year", "fp": "fiscal_period"})
        df = df.sort_values("end_date", ascending=False)

        expected_cols = [
            "concept",
            "unit",
            "value",
            "end_date",
            "start_date",
            "fiscal_year",
            "fiscal_period",
            "form",
            "filed",
            "accn",
        ]
        existing_cols = [col for col in expected_cols if col in df.columns]
        return df[existing_cols].reset_index(drop=True)

    def get_key_financials(self, cik_or_ticker: str, use_bulk: bool = False) -> pd.DataFrame:
        """Retrieves and consolidates crucial fundamental financial indicators."""
        company_facts = self.get_company_facts(cik_or_ticker, use_bulk=use_bulk)
        if not company_facts:
            return pd.DataFrame()

        key_concepts = [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "NetIncomeLoss",
            "Assets",
            "Liabilities",
            "StockholdersEquity",
            "OperatingIncomeLoss",
            "GrossProfit",
            "CashAndCashEquivalentsAtCarryingValue",
            "LongTermDebt",
            "EarningsPerShareBasic",
            "EarningsPerShareDiluted",
        ]

        all_data = []
        for concept in key_concepts:
            df = self.extract_financial_metric(company_facts, concept)
            if not df.empty and "form" in df.columns:
                df_filtered = df[df["form"].isin(["10-K", "10-Q"])]
                if not df_filtered.empty:
                    all_data.append(df_filtered)

        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    def _recent_submissions_to_dataframe(self, submissions: Dict[str, Any], cik: str) -> pd.DataFrame:
        """Transforms company submission indices into flat pandas matrices."""
        recent = submissions.get("filings", {}).get("recent", {})
        if not recent:
            return pd.DataFrame()

        df = pd.DataFrame(recent)
        if df.empty:
            return df

        for col in ["filingDate", "reportDate"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        df["cik"] = str(cik).zfill(10)
        df["company_name"] = submissions.get("name", "")
        df["tickers"] = str(submissions.get("tickers", []))

        # Re-map standard properties for legacy components
        for source_col, target_col in [
            ("accessionNumber", "accession_number"),
            ("filingDate", "filing_date"),
            ("reportDate", "report_date"),
        ]:
            if source_col in df.columns:
                df[target_col] = df[source_col]
        return df

    def get_recent_filings(self, cik_or_ticker: str, form_types: Optional[List[str]] = None, use_bulk: bool = False) -> pd.DataFrame:
        """Collects historical lists of recent submissions."""
        submissions = self.get_company_submissions(cik_or_ticker, use_bulk=use_bulk)
        if not submissions:
            return pd.DataFrame()

        cik = self.lookup_cik(cik_or_ticker) if not cik_or_ticker.isdigit() else cik_or_ticker
        df = self._recent_submissions_to_dataframe(submissions, cik)

        if form_types and not df.empty and "form" in df.columns:
            df = df[df["form"].isin(form_types)]
        return df

    def get_sec_filings(self, ticker: str, form_type: Optional[str] = None, limit: int = 10, use_bulk: bool = False) -> List[Dict[str, Any]]:
        """Wraps sub-calls to generate JSON lists for downstream API/Chart rendering."""
        form_types = [form_type] if form_type else None
        df = self.get_recent_filings(ticker, form_types=form_types, use_bulk=use_bulk)
        if df.empty:
            return []

        if "filingDate" in df.columns:
            df = df.sort_values("filingDate", ascending=False)
        return df.head(limit).to_dict(orient="records")

    def get_13f_holdings(self, cik_or_ticker: str, use_bulk: bool = False) -> pd.DataFrame:
        """Tracks institution filings for Form 13F schedules."""
        return self.get_recent_filings(cik_or_ticker, form_types=["13F-HR", "13F-HR/A"], use_bulk=use_bulk)

    # =============================================================================
    # Financial Statement Data Sets (FSDS) Engine
    # =============================================================================

    def download_financial_statement_data(self, year: int, quarter: int) -> Dict[str, pd.DataFrame]:
        """Loads SEC FSDS zip datasets into memory structures."""
        filename = f"{year}q{quarter}.zip"
        url = f"{self.SEC_FSDS_URL}/{filename}"
        cache_file = self.cache_dir / filename

        try:
            if cache_file.exists():
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=30):
                    with zipfile.ZipFile(cache_file, "r") as zf:
                        return self._parse_fsds_zip(zf)

            response = self._download_with_retry(url)
            if response is None:
                self._notify(f"FSDS historical dataset for {year}Q{quarter} not found.")
                return {}

            cache_file.write_bytes(response.content)
            with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
                return self._parse_fsds_zip(zf)

        except Exception as e:
            self._notify(f"Error loading quarterly FSDS files: {e}", "error")
            return {}

    def _parse_fsds_zip(self, zf: zipfile.ZipFile) -> Dict[str, pd.DataFrame]:
        """Deconstructs text matrices packed inside FSDS zip containers."""
        result = {}
        file_mapping = {"sub.txt": "sub", "num.txt": "num", "pre.txt": "pre", "tag.txt": "tag"}

        for filename, key in file_mapping.items():
            try:
                with zf.open(filename) as f:
                    result[key] = pd.read_csv(f, sep="\t", low_memory=False)
            except Exception as e:
                self._notify(f"Could not parse sub-file {filename}: {e}")
                result[key] = pd.DataFrame()
        return result

    def get_company_financials(self, fsds_data: Dict[str, pd.DataFrame], cik: Optional[str] = None, ticker: Optional[str] = None) -> pd.DataFrame:
        """Constructs balanced company ledger matrices using loaded FSDS components."""
        if not fsds_data or "sub" not in fsds_data or "num" not in fsds_data:
            return pd.DataFrame()

        sub_df = fsds_data["sub"]
        num_df = fsds_data["num"]

        if cik:
            sub_filtered = sub_df[sub_df["cik"] == int(cik)]
        elif ticker:
            sub_filtered = sub_df[sub_df["instance"].str.upper().str.contains(ticker.upper(), na=False)]
        else:
            return pd.DataFrame()

        if sub_filtered.empty:
            return pd.DataFrame()

        adshs = sub_filtered["adsh"].unique()
        company_nums = num_df[num_df["adsh"].isin(adshs)]

        return company_nums.merge(sub_filtered[["adsh", "cik", "name", "form", "filed", "period"]], on="adsh", how="left")

    # =============================================================================
    # Fails-To-Deliver Data Engine
    # =============================================================================

    def download_fails_to_deliver(self, year: int, half: int) -> pd.DataFrame:
        """Retrieves and caches Fails-to-Deliver dataset matrices."""
        suffix = "a" if half == 1 else "b"
        filename = f"cnsfails{year}{half:02d}{suffix}.zip"
        url = f"{self.SEC_FTD_URL}/{filename}"
        cache_file = self.cache_dir / filename

        try:
            if cache_file.exists():
                cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if cache_age < timedelta(days=30):
                    with zipfile.ZipFile(cache_file, "r") as zf:
                        return self._parse_ftd_zip(zf)

            response = self._download_with_retry(url)
            if response is None:
                self._notify(f"Fails-to-deliver data for {year} H{half} not found.")
                return pd.DataFrame()

            cache_file.write_bytes(response.content)
            with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
                return self._parse_ftd_zip(zf)

        except Exception as e:
            self._notify(f"FTD download execution error: {e}", "error")
            return pd.DataFrame()

    def _parse_ftd_zip(self, zf: zipfile.ZipFile) -> pd.DataFrame:
        """Processes flat files inside Fails-to-deliver archives."""
        all_data = []
        for filename in zf.namelist():
            if filename.endswith(".txt"):
                try:
                    with zf.open(filename) as f:
                        df = pd.read_csv(f, sep="|", encoding="latin-1", low_memory=False)
                        all_data.append(df)
                except Exception as e:
                    self._notify(f"Could not parse fails flatfile {filename}: {e}")

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            result.columns = result.columns.str.strip().str.lower().str.replace(" ", "_")

            if "settlement_date" in result.columns:
                result["settlement_date"] = pd.to_datetime(result["settlement_date"], format="%Y%m%d", errors="coerce")
            return result
        return pd.DataFrame()

    # =============================================================================
    # Refresh Schedules
    # =============================================================================

    def refresh_reference_data(self, force: bool = False) -> Dict[str, Optional[str]]:
        """Re-syncs global reference indexes."""
        refreshed: Dict[str, Optional[str]] = {}
        for dataset_name in self.BULK_DATASETS:
            archive_path = self.download_bulk_archive(dataset_name, force=force)
            refreshed[dataset_name] = str(archive_path) if archive_path else None

        tickers_path = self._ensure_cached_reference_file(
            cache_name="company_tickers.json",
            url=self.SEC_COMPANY_TICKERS_URL,
            force=force,
        )
        refreshed["company_tickers"] = str(tickers_path) if tickers_path else None
        return refreshed

    def refresh_bulk_data(self, tickers: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
        """Manages bulk updates across scheduled target lists."""
        refresh_status = self.refresh_reference_data(force=force)
        hydrated_facts = 0
        hydrated_filings = 0
        processed_tickers = 0

        tickers = [t.upper() for t in (tickers or []) if t]
        if not tickers:
            return {
                "refreshed": refresh_status,
                "processed_tickers": processed_tickers,
                "company_facts_rows": hydrated_facts,
                "filings_rows": hydrated_filings,
            }

        tickers_df = self.get_company_tickers_df()
        if tickers_df.empty:
            return {
                "refreshed": refresh_status,
                "processed_tickers": processed_tickers,
                "company_facts_rows": hydrated_facts,
                "filings_rows": hydrated_filings,
            }

        for ticker in tickers:
            cik = self._cik_by_ticker_cache.get(ticker)
            if not cik:
                continue

            processed_tickers += 1
            submissions = self.get_company_submissions(cik, use_bulk=True)
            if submissions:
                hydrated_filings += self.save_recent_filings_to_db(cik, submissions)

            company_facts = self.get_company_facts(cik, use_bulk=True)
            if company_facts:
                hydrated_facts += self.save_company_facts_to_db(cik, company_facts)

        return {
            "refreshed": refresh_status,
            "processed_tickers": processed_tickers,
            "company_facts_rows": hydrated_facts,
            "filings_rows": hydrated_filings,
        }

    # =============================================================================
    # Database Persistence Operations
    # =============================================================================

    def save_recent_filings_to_db(self, cik: str, submissions: Dict[str, Any]) -> int:
        """Saves company filing indices inside DB tables."""
        if not self._check_db_available():
            return 0

        filings_df = self._recent_submissions_to_dataframe(submissions, cik)
        if filings_df.empty:
            return 0

        try:
            from modules.database import insert_sec_filings

            return insert_sec_filings(filings_df)
        except Exception as exc:
            self._notify(f"Could not write recent SEC filings index to database for CIK {cik}: {exc}")
            return 0

    def save_company_facts_to_db(self, cik: str, company_facts: Dict[str, Any]) -> int:
        """Saves compiled company facts inside database tables."""
        if not self._check_db_available():
            return 0

        company_facts_df = self.company_facts_to_dataframe(company_facts)
        if company_facts_df.empty:
            return 0

        db = get_db_connection()
        try:
            db.insert_df(
                company_facts_df,
                "sec_company_facts",
                if_exists="append",
                conflict_columns=["cik", "concept", "end_date", "unit"] if {"cik", "concept", "end_date", "unit"}.issubset(company_facts_df.columns) else None,
            )
            return len(company_facts_df)
        except Exception as e:
            self._notify(f"Could not persist parsed company facts to database schema: {e}")
            return 0

    def save_financial_statements_to_db(self, fsds_data: Dict[str, pd.DataFrame], year: int, quarter: int) -> int:
        """Saves FSDS numerical structures directly into database tables."""
        if not self._check_db_available():
            return 0

        db = get_db_connection()
        total_records = 0

        if "num" in fsds_data and not fsds_data["num"].empty:
            num_df = fsds_data["num"].copy()
            num_df["data_year"] = year
            num_df["data_quarter"] = quarter

            try:
                db.insert_df(
                    num_df,
                    "sec_financial_statements",
                    if_exists="append",
                    conflict_columns=["adsh", "tag", "ddate"] if {"adsh", "tag", "ddate"}.issubset(num_df.columns) else None,
                )
                total_records += len(num_df)
            except Exception as e:
                self._notify(f"Could not save numerical FSDS indicators to db: {e}")

        if "sub" in fsds_data and not fsds_data["sub"].empty:
            sub_df = fsds_data["sub"].copy()
            sub_df["data_year"] = year
            sub_df["data_quarter"] = quarter

            try:
                db.insert_df(
                    sub_df,
                    "sec_submissions",
                    if_exists="append",
                    conflict_columns=["adsh"] if "adsh" in sub_df.columns else None,
                )
                total_records += len(sub_df)
            except Exception as e:
                self._notify(f"Could not save submission indicators to db: {e}")
        return total_records


# =============================================================================
# Absolute Module-Level backward compatibility wrappers
# =============================================================================

_default_client = SECDataLoader()


def lookup_cik(ticker: str) -> Optional[str]:
    return _default_client.lookup_cik(ticker)


def get_company_tickers() -> pd.DataFrame:
    return _default_client.get_company_tickers_df()


def get_company_facts(cik: str, use_bulk: bool = False) -> Dict[str, Any]:
    return _default_client.get_company_facts(cik, use_bulk=use_bulk)


def get_company_submissions(cik: str, use_bulk: bool = False) -> Dict[str, Any]:
    return _default_client.get_company_submissions(cik, use_bulk=use_bulk)


def extract_financial_metric(company_facts: Dict, concept: str, taxonomy: str = "us-gaap") -> pd.DataFrame:
    return _default_client.extract_financial_metric(company_facts, concept, taxonomy)


def get_key_financials(cik: str, use_bulk: bool = False) -> pd.DataFrame:
    return _default_client.get_key_financials(cik, use_bulk=use_bulk)


def get_recent_filings(cik: str, form_types: Optional[List[str]] = None, use_bulk: bool = False) -> pd.DataFrame:
    return _default_client.get_recent_filings(cik, form_types=form_types, use_bulk=use_bulk)


def get_sec_filings(ticker: str, form_type: Optional[str] = None, limit: int = 10, use_bulk: bool = False) -> List[Dict[str, Any]]:
    return _default_client.get_sec_filings(ticker, form_type=form_type, limit=limit, use_bulk=use_bulk)


def get_13f_holdings(cik: str, filing_date: Optional[str] = None) -> pd.DataFrame:
    return _default_client.get_13f_holdings(cik)


def download_fails_to_deliver(year: int, half: int) -> pd.DataFrame:
    return _default_client.download_fails_to_deliver(year, half)


def download_financial_statement_data(year: int, quarter: int) -> Dict[str, pd.DataFrame]:
    return _default_client.download_financial_statement_data(year, quarter)


def refresh_sec_reference_data(force: bool = False) -> Dict[str, Optional[str]]:
    return _default_client.refresh_reference_data(force=force)


def refresh_sec_bulk_data(tickers: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
    return _default_client.refresh_bulk_data(tickers=tickers, force=force)


def save_recent_filings_to_db(cik: str, submissions: Dict[str, Any]) -> int:
    return _default_client.save_recent_filings_to_db(cik, submissions)


def save_company_facts_to_db(cik: str, company_facts: Dict) -> int:
    return _default_client.save_company_facts_to_db(cik, company_facts)


def save_financial_statements_to_db(fsds_data: Dict[str, pd.DataFrame], year: int, quarter: int) -> int:
    return _default_client.save_financial_statements_to_db(fsds_data, year, quarter)
