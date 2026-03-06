"""
License monitoring API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List
import uuid

from app.database import get_db
from app.auth.api_key import get_current_user
from app.models import User, LicenseMonitor, ProfessionalLicense, LicenseAlertSent
from app.schemas import (
    MonitoringSubscribeRequest,
    MonitoringSubscribeResponse,
    MonitoringListResponse,
    MonitoredLicenseResponse
)

router = APIRouter(prefix="/monitor", tags=["Monitoring"])


@router.post("/subscribe", response_model=MonitoringSubscribeResponse)
async def subscribe_to_monitoring(
    request: MonitoringSubscribeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Subscribe to license expiration monitoring
    
    **Features:**
    - Get automatic alerts before license expires
    - Configurable alert timing (90, 60, 30, 7, 1 days before)
    - Email and webhook notifications
    - Status change alerts (suspended, revoked)
    
    **Example:**
    ```json
    {
      "license_id": 42,
      "alert_at_days": [90, 60, 30, 7, 1],
      "email": "recruiter@agency.com",
      "webhook_url": "https://your-ats.com/webhooks/license-alert"
    }
    ```
    """
    # Check if license exists
    license = db.query(ProfessionalLicense).filter(
        ProfessionalLicense.id == request.license_id
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found"
        )
    
    # Check if already monitoring
    existing_monitor = db.query(LicenseMonitor).filter(
        LicenseMonitor.license_id == request.license_id,
        LicenseMonitor.subscriber_id == user.id
    ).first()
    
    if existing_monitor:
        # Update existing monitor
        existing_monitor.alert_at_days = request.alert_at_days
        existing_monitor.email_addresses = [request.email] if request.email else []
        existing_monitor.webhook_url = request.webhook_url
        existing_monitor.is_active = True
        existing_monitor.updated_at = datetime.utcnow()
        monitor = existing_monitor
    else:
        # Create new monitor
        monitor = LicenseMonitor(
            monitor_id=str(uuid.uuid4()),
            license_id=request.license_id,
            subscriber_id=user.id,
            alert_at_days=request.alert_at_days,
            email_addresses=[request.email] if request.email else [],
            webhook_url=request.webhook_url,
            is_active=True
        )
        db.add(monitor)
    
    db.commit()
    db.refresh(monitor)
    
    # Calculate days until expiration
    days_until = (license.expiration_date - date.today()).days
    
    # Find next alert date
    next_alert_days = None
    for days in sorted(request.alert_at_days, reverse=True):
        if days_until > days:
            next_alert_days = days
            break
    
    next_alert_date = None
    if next_alert_days is not None:
        next_alert_date = license.expiration_date - timedelta(days=next_alert_days)
    
    professional_name = f"{license.first_name} {license.last_name}" if license.first_name else "Professional"
    
    return MonitoringSubscribeResponse(
        monitor_id=monitor.monitor_id,
        status="active",
        monitoring={
            "professional": professional_name,
            "license": f"{license.state_code} #{license.license_number}",
            "expires": license.expiration_date.isoformat(),
            "days_until_expiration": days_until
        },
        next_alert=next_alert_date,
        alerts_configured=[
            f"{days} days before expiration" for days in request.alert_at_days
        ]
    )


@router.get("/my-monitors", response_model=MonitoringListResponse)
async def get_my_monitors(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all licenses you're currently monitoring
    """
    monitors = db.query(LicenseMonitor).filter(
        LicenseMonitor.subscriber_id == user.id,
        LicenseMonitor.is_active == True
    ).all()
    
    monitor_list = []
    status_counts = {
        "expiring_soon": 0,
        "active": 0,
        "expired": 0
    }
    
    for monitor in monitors:
        license = db.query(ProfessionalLicense).filter(
            ProfessionalLicense.id == monitor.license_id
        ).first()
        
        if not license:
            continue
        
        days_until = (license.expiration_date - date.today()).days
        
        # Determine priority
        if days_until < 0:
            priority = "critical"
            status_counts["expired"] += 1
        elif days_until <= 30:
            priority = "high"
            status_counts["expiring_soon"] += 1
        else:
            priority = "normal"
            status_counts["active"] += 1
        
        # Find next alert
        next_alert = None
        for days in sorted(monitor.alert_at_days, reverse=True):
            if days_until > days:
                next_alert = license.expiration_date - timedelta(days=days)
                break
        
        professional_name = f"{license.first_name} {license.last_name}" if license.first_name else None
        
        monitor_list.append(MonitoredLicenseResponse(
            monitor_id=monitor.monitor_id,
            professional_name=professional_name,
            license_number=license.license_number,
            state=license.state_code,
            type=license.license_type,
            status=license.status,
            expires=license.expiration_date,
            days_until_expiration=days_until,
            next_alert=next_alert,
            priority=priority
        ))
    
    return MonitoringListResponse(
        total_monitoring=len(monitors),
        by_status=status_counts,
        monitors=monitor_list
    )


@router.delete("/{monitor_id}")
async def stop_monitoring(
    monitor_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stop monitoring a license
    """
    monitor = db.query(LicenseMonitor).filter(
        LicenseMonitor.monitor_id == monitor_id,
        LicenseMonitor.subscriber_id == user.id
    ).first()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )
    
    # Count total alerts sent
    alerts_sent = db.query(LicenseAlertSent).filter(
        LicenseAlertSent.monitor_id == monitor.id
    ).count()
    
    # Deactivate monitor (don't delete for audit trail)
    monitor.is_active = False
    monitor.updated_at = datetime.utcnow()
    db.commit()
    
    license = db.query(ProfessionalLicense).filter(
        ProfessionalLicense.id == monitor.license_id
    ).first()
    
    professional_name = f"{license.first_name} {license.last_name}" if license and license.first_name else "Professional"
    
    return {
        "message": f"Monitoring stopped for {professional_name}'s {license.state_code if license else ''} license",
        "monitor_id": monitor_id,
        "alerts_sent_total": alerts_sent,
        "was_active": True
    }


@router.get("/alerts/{monitor_id}")
async def get_alert_history(
    monitor_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get history of alerts sent for a monitored license
    """
    monitor = db.query(LicenseMonitor).filter(
        LicenseMonitor.monitor_id == monitor_id,
        LicenseMonitor.subscriber_id == user.id
    ).first()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )
    
    alerts = db.query(LicenseAlertSent).filter(
        LicenseAlertSent.monitor_id == monitor.id
    ).order_by(LicenseAlertSent.sent_at.desc()).all()
    
    return {
        "monitor_id": monitor_id,
        "total_alerts": len(alerts),
        "alerts": [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "days_until_expiration": alert.days_until_expiration,
                "severity": alert.severity,
                "sent_at": alert.sent_at,
                "sent_via": alert.sent_via,
                "delivery_status": alert.delivery_status
            }
            for alert in alerts
        ]
    }


from datetime import timedelta  # Add to imports at top
