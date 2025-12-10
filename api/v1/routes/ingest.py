"""
Data Ingestion API Routes

Endpoints for ingesting data from external sources or manual uploads.
These endpoints validate and write data to the database.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import pandas as pd
import io
import logging

from modules.database import get_db_connection
from modules.validation import validate_and_clean
from modules.database.queries import (
    insert_fred_data,
    insert_stock_data,
    insert_options_data,
)
from api.v1.dependencies.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request validation
class FREDDataPoint(BaseModel):
    """Single FRED data point."""
    series_id: str = Field(..., max_length=100)
    date: date
    value: Optional[float] = None


class StockOHLCVDataPoint(BaseModel):
    """Single stock OHLCV data point."""
    ticker: str = Field(..., max_length=20)
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[int] = None
    adj_close: Optional[float] = None


class IngestionResponse(BaseModel):
    """Response for data ingestion operations."""
    success: bool
    records_received: int
    records_validated: int
    records_inserted: int
    errors: Optional[List[str]] = None
    message: str


class IngestionStatus(BaseModel):
    """Status of a background ingestion job."""
    job_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: Optional[float] = None
    message: Optional[str] = None


# In-memory job tracker (use Redis in production)
ingestion_jobs = {}


@router.post("/ingest/fred", response_model=IngestionResponse, tags=["Ingestion"])
async def ingest_fred_data(
    data: List[FREDDataPoint],
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest FRED economic data.
    
    Validates and inserts FRED time series data into the database.
    Duplicates (same series_id and date) will be updated.
    
    **Authentication required.**
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame([d.model_dump() for d in data])
        
        logger.info(f"Received {len(df)} FRED records for ingestion")
        
        # Validate
        validated_df = validate_and_clean(df, 'fred', raise_errors=True)
        
        # Insert
        records_inserted = insert_fred_data(validated_df)
        
        return IngestionResponse(
            success=True,
            records_received=len(df),
            records_validated=len(validated_df),
            records_inserted=records_inserted,
            message=f"Successfully inserted {records_inserted} FRED records"
        )
    
    except Exception as e:
        logger.error(f"Error ingesting FRED data: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingest/stock", response_model=IngestionResponse, tags=["Ingestion"])
async def ingest_stock_data(
    data: List[StockOHLCVDataPoint],
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest stock OHLCV data.
    
    Validates and inserts stock price data into the database.
    Duplicates (same ticker and date) will be updated.
    
    **Authentication required.**
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame([d.model_dump() for d in data])
        
        logger.info(f"Received {len(df)} stock records for ingestion")
        
        # Validate
        validated_df = validate_and_clean(df, 'stock', raise_errors=True)
        
        # Insert
        records_inserted = insert_stock_data(validated_df)
        
        return IngestionResponse(
            success=True,
            records_received=len(df),
            records_validated=len(validated_df),
            records_inserted=records_inserted,
            message=f"Successfully inserted {records_inserted} stock records"
        )
    
    except Exception as e:
        logger.error(f"Error ingesting stock data: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingest/csv/{data_type}", response_model=IngestionResponse, tags=["Ingestion"])
async def ingest_csv_file(
    data_type: str,
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest data from CSV file.
    
    **Supported data types:**
    - `fred`: FRED economic data
    - `stock`: Stock OHLCV data
    - `options`: Options data
    - `ici_weekly`: ICI weekly ETF flows
    - `cboe_vix`: CBOE VIX historical data
    
    CSV must have appropriate columns for the data type.
    
    **Authentication required.**
    """
    supported_types = ['fred', 'stock', 'options', 'ici_weekly', 'cboe_vix']
    
    if data_type not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported data type. Supported: {supported_types}"
        )
    
    try:
        # Read CSV
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        logger.info(f"Received CSV with {len(df)} records for {data_type}")
        
        # Validate
        validated_df = validate_and_clean(df, data_type, raise_errors=True)
        
        # Insert based on type
        if data_type == 'fred':
            records_inserted = insert_fred_data(validated_df)
        elif data_type == 'stock':
            records_inserted = insert_stock_data(validated_df)
        elif data_type == 'options':
            records_inserted = insert_options_data(validated_df)
        else:
            # For other types, use generic insert
            from modules.database.queries import insert_generic_data
            table_name = f"{data_type}_data" if data_type == 'ici_weekly' else f"{data_type}_history"
            records_inserted = insert_generic_data(validated_df, table_name)
        
        return IngestionResponse(
            success=True,
            records_received=len(df),
            records_validated=len(validated_df),
            records_inserted=records_inserted,
            message=f"Successfully inserted {records_inserted} {data_type} records"
        )
    
    except Exception as e:
        logger.error(f"Error ingesting CSV file: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingest/bulk/{data_type}", response_model=IngestionStatus, tags=["Ingestion"])
async def ingest_bulk_data(
    data_type: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Ingest large CSV file in the background.
    
    For large datasets, this endpoint processes the file asynchronously
    and returns a job ID to check status.
    
    Use `GET /ingest/status/{job_id}` to check progress.
    
    **Authentication required.**
    """
    import uuid
    
    job_id = str(uuid.uuid4())
    
    # Store job
    ingestion_jobs[job_id] = {
        'status': 'pending',
        'progress': 0.0,
        'message': 'Job queued',
        'created_at': datetime.utcnow()
    }
    
    # Add background task
    async def process_bulk_ingestion():
        try:
            ingestion_jobs[job_id]['status'] = 'processing'
            ingestion_jobs[job_id]['message'] = 'Reading file...'
            
            contents = await file.read()
            df = pd.read_csv(io.BytesIO(contents))
            
            ingestion_jobs[job_id]['progress'] = 0.3
            ingestion_jobs[job_id]['message'] = f'Validating {len(df)} records...'
            
            validated_df = validate_and_clean(df, data_type, raise_errors=False)
            
            ingestion_jobs[job_id]['progress'] = 0.6
            ingestion_jobs[job_id]['message'] = f'Inserting {len(validated_df)} records...'
            
            # Insert in chunks for large datasets
            chunk_size = 5000
            total_inserted = 0
            
            for i in range(0, len(validated_df), chunk_size):
                chunk = validated_df.iloc[i:i+chunk_size]
                
                if data_type == 'fred':
                    total_inserted += insert_fred_data(chunk)
                elif data_type == 'stock':
                    total_inserted += insert_stock_data(chunk)
                
                progress = 0.6 + (0.4 * (i + len(chunk)) / len(validated_df))
                ingestion_jobs[job_id]['progress'] = progress
            
            ingestion_jobs[job_id]['status'] = 'completed'
            ingestion_jobs[job_id]['progress'] = 1.0
            ingestion_jobs[job_id]['message'] = f'Successfully inserted {total_inserted} records'
            
        except Exception as e:
            logger.error(f"Background ingestion failed: {e}")
            ingestion_jobs[job_id]['status'] = 'failed'
            ingestion_jobs[job_id]['message'] = str(e)
    
    background_tasks.add_task(process_bulk_ingestion)
    
    return IngestionStatus(
        job_id=job_id,
        status='pending',
        progress=0.0,
        message='Job queued for processing'
    )


@router.get("/ingest/status/{job_id}", response_model=IngestionStatus, tags=["Ingestion"])
async def get_ingestion_status(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Check status of a background ingestion job.
    
    Returns the current status and progress of the job.
    
    **Authentication required.**
    """
    if job_id not in ingestion_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = ingestion_jobs[job_id]
    
    return IngestionStatus(
        job_id=job_id,
        status=job['status'],
        progress=job.get('progress'),
        message=job.get('message')
    )


@router.delete("/ingest/job/{job_id}", tags=["Ingestion"])
async def delete_ingestion_job(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a completed or failed ingestion job from the queue.
    
    **Authentication required.**
    """
    if job_id not in ingestion_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = ingestion_jobs[job_id]['status']
    if job_status not in ['completed', 'failed']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete job with status: {job_status}"
        )
    
    del ingestion_jobs[job_id]
    
    return {"message": "Job deleted successfully"}
