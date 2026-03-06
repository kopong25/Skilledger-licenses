"""
Bulk verification API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
import csv
import io
import uuid
from typing import List

from app.database import get_db
from app.auth.api_key import get_current_user, get_current_active_subscription
from app.models import User, BulkVerificationJob, BulkVerificationResult
from app.schemas import BulkJobStatus, BulkVerificationResults
from app.services.state_boards import StateBoardAdapterFactory
from app.config import settings

router = APIRouter(prefix="/bulk", tags=["Bulk Verification"])


@router.post("/upload", response_model=dict)
async def upload_bulk_verification(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    subscription = Depends(get_current_active_subscription),
    db: Session = Depends(get_db)
):
    """
    Upload CSV file for bulk license verification
    
    **CSV Format:**
    ```csv
    license_number,state,candidate_name
    123456,AZ,Jane Doe
    789012,CA,John Smith
    345678,TX,Mary Johnson
    ```
    
    **Response:**
    Returns job_id to track progress
    """
    # Validate file is CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be CSV format"
        )
    
    # Read CSV file
    contents = await file.read()
    csv_data = contents.decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    licenses_to_verify = []
    
    required_fields = ['license_number', 'state']
    for row_num, row in enumerate(csv_reader, start=1):
        # Validate required fields
        if not all(field in row for field in required_fields):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row {row_num}: Missing required fields. Need: {required_fields}"
            )
        
        licenses_to_verify.append({
            'row_number': row_num,
            'license_number': row['license_number'].strip(),
            'state_code': row['state'].strip().upper(),
            'candidate_name': row.get('candidate_name', '').strip()
        })
    
    if len(licenses_to_verify) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty or has no valid rows"
        )
    
    if len(licenses_to_verify) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 licenses per bulk upload. Please split into smaller batches."
        )
    
    # Create bulk job
    job = BulkVerificationJob(
        job_id=str(uuid.uuid4()),
        requester_id=user.id,
        total_licenses=len(licenses_to_verify),
        status='queued'
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Process verifications (in production, this would be async/background task)
    # For MVP, we'll process synchronously with a limit
    if len(licenses_to_verify) <= 50:
        # Process small batches immediately
        await _process_bulk_job(job.id, licenses_to_verify, db)
        status_text = "completed"
        estimated_time = "Complete"
    else:
        # Queue larger batches for background processing
        status_text = "queued"
        estimated_time = f"{len(licenses_to_verify) * 2} seconds"
    
    return {
        "job_id": job.job_id,
        "status": status_text,
        "total_licenses": len(licenses_to_verify),
        "estimated_completion": estimated_time,
        "webhook_will_notify": False
    }


@router.get("/status/{job_id}", response_model=BulkJobStatus)
async def get_bulk_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check status of bulk verification job
    """
    job = db.query(BulkVerificationJob).filter(
        BulkVerificationJob.job_id == job_id,
        BulkVerificationJob.requester_id == user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    percentage = (job.completed_licenses / job.total_licenses * 100) if job.total_licenses > 0 else 0
    
    # Estimate completion time
    estimated_completion = None
    if job.status == 'processing' and job.started_at:
        # Rough estimate: 2 seconds per license
        remaining = job.total_licenses - job.completed_licenses
        estimated_seconds = remaining * 2
        estimated_completion = datetime.utcnow().isoformat()
    
    return BulkJobStatus(
        job_id=job.job_id,
        status=job.status,
        total=job.total_licenses,
        completed=job.completed_licenses,
        successful=job.successful_verifications,
        failed=job.failed_verifications,
        percentage=percentage,
        estimated_completion_time=estimated_completion
    )


@router.get("/results/{job_id}", response_model=BulkVerificationResults)
async def get_bulk_results(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download results of bulk verification job
    """
    job = db.query(BulkVerificationJob).filter(
        BulkVerificationJob.job_id == job_id,
        BulkVerificationJob.requester_id == user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is still {job.status}. Wait for completion."
        )
    
    # Get results
    results = db.query(BulkVerificationResult).filter(
        BulkVerificationResult.bulk_job_id == job.id
    ).order_by(BulkVerificationResult.row_number).all()
    
    # Generate CSV (in production, this would be stored in S3)
    csv_output = io.StringIO()
    csv_writer = csv.writer(csv_output)
    
    # Header
    csv_writer.writerow([
        'row', 'license_number', 'state', 'candidate_name', 'status',
        'license_type', 'expiration_date', 'discipline_record', 
        'verified_at', 'error_message'
    ])
    
    # Data
    for result in results:
        csv_writer.writerow([
            result.row_number,
            result.license_number,
            result.state_code,
            result.candidate_name or '',
            result.verification_status,
            result.license_type or '',
            result.expiration_date.isoformat() if result.expiration_date else '',
            'Yes' if result.discipline_record else 'No',
            result.verified_at.isoformat() if result.verified_at else '',
            result.error_message or ''
        ])
    
    results_csv = csv_output.getvalue()
    
    # Count statuses
    summary = {
        "total_processed": job.total_licenses,
        "verified": job.successful_verifications,
        "not_found": sum(1 for r in results if r.verification_status == 'not_found'),
        "errors": job.failed_verifications,
        "active_licenses": sum(1 for r in results if r.status == 'active'),
        "expired_licenses": sum(1 for r in results if r.status == 'expired')
    }
    
    return BulkVerificationResults(
        job_id=job.job_id,
        status=job.status,
        results_url=f"/api/bulk/download/{job_id}",  # Would be S3 URL in production
        summary=summary,
        download_formats=["csv"]
    )


async def _process_bulk_job(
    job_id: int,
    licenses: List[dict],
    db: Session
):
    """
    Process bulk verification job
    (In production, this would be a Celery/background task)
    """
    job = db.query(BulkVerificationJob).filter(
        BulkVerificationJob.id == job_id
    ).first()
    
    job.status = 'processing'
    job.started_at = datetime.utcnow()
    db.commit()
    
    for license_data in licenses:
        try:
            # Verify license
            adapter = StateBoardAdapterFactory.get_adapter(
                license_data['state_code'],
                "RN",
                {"nursys": settings.NURSYS_API_KEY}
            )
            
            result = await adapter.verify_license(
                license_data['license_number'],
                license_data['state_code']
            )
            
            # Create result record
            if result.get('status') in ['active', 'expired', 'suspended']:
                verification_status = 'verified'
                job.successful_verifications += 1
            elif result.get('status') == 'not_found':
                verification_status = 'not_found'
            else:
                verification_status = 'error'
                job.failed_verifications += 1
            
            bulk_result = BulkVerificationResult(
                bulk_job_id=job.id,
                row_number=license_data['row_number'],
                license_number=license_data['license_number'],
                state_code=license_data['state_code'],
                candidate_name=license_data.get('candidate_name'),
                verification_status=verification_status,
                license_type=result.get('license_type'),
                status=result.get('status'),
                expiration_date=result.get('expiration_date'),
                discipline_record=result.get('discipline_record', False),
                verified_at=datetime.utcnow(),
                error_message=result.get('error')
            )
            db.add(bulk_result)
            
        except Exception as e:
            # Handle errors
            bulk_result = BulkVerificationResult(
                bulk_job_id=job.id,
                row_number=license_data['row_number'],
                license_number=license_data['license_number'],
                state_code=license_data['state_code'],
                candidate_name=license_data.get('candidate_name'),
                verification_status='error',
                error_message=str(e)
            )
            db.add(bulk_result)
            job.failed_verifications += 1
        
        # Update progress
        job.completed_licenses += 1
        job.progress_percentage = (job.completed_licenses / job.total_licenses) * 100
        db.commit()
    
    # Mark complete
    job.status = 'completed'
    job.completed_at = datetime.utcnow()
    db.commit()
