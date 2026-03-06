"""
License expiration monitoring service
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import httpx
from loguru import logger

from app.models import LicenseMonitor, ProfessionalLicense, LicenseAlertSent, User


class MonitoringService:
    """
    Service for managing license expiration monitoring
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def check_expirations(self) -> Dict[str, int]:
        """
        Check all monitored licenses for upcoming expirations
        Called by daily cron job
        
        Returns:
            Statistics about alerts sent
        """
        stats = {
            "checked": 0,
            "alerts_sent": 0,
            "errors": 0
        }
        
        # Get all active monitors
        monitors = self.db.query(LicenseMonitor).filter(
            LicenseMonitor.is_active == True
        ).all()
        
        for monitor in monitors:
            stats["checked"] += 1
            
            try:
                alerts_sent = await self._check_single_monitor(monitor)
                stats["alerts_sent"] += alerts_sent
            except Exception as e:
                logger.error(f"Error checking monitor {monitor.id}: {str(e)}")
                stats["errors"] += 1
        
        return stats
    
    async def _check_single_monitor(self, monitor: LicenseMonitor) -> int:
        """
        Check a single monitored license and send alerts if needed
        
        Returns:
            Number of alerts sent
        """
        license = self.db.query(ProfessionalLicense).filter(
            ProfessionalLicense.id == monitor.license_id
        ).first()
        
        if not license:
            logger.warning(f"License not found for monitor {monitor.id}")
            return 0
        
        # Calculate days until expiration
        days_until = (license.expiration_date - date.today()).days
        
        alerts_sent = 0
        
        # Check if we should send alert
        if days_until in monitor.alert_at_days:
            # Check if we already sent this alert
            existing_alert = self.db.query(LicenseAlertSent).filter(
                LicenseAlertSent.monitor_id == monitor.id,
                LicenseAlertSent.days_until_expiration == days_until
            ).first()
            
            if not existing_alert:
                # Send alert
                await self._send_alert(monitor, license, days_until)
                alerts_sent += 1
        
        # Check for status changes (expired, suspended, etc.)
        if license.status != "active" and license.status != "expired":
            await self._send_status_change_alert(monitor, license)
            alerts_sent += 1
        
        # Update monitor
        monitor.last_checked_at = datetime.utcnow()
        self.db.commit()
        
        return alerts_sent
    
    async def _send_alert(
        self,
        monitor: LicenseMonitor,
        license: ProfessionalLicense,
        days_until: int
    ):
        """
        Send expiration alert via configured methods
        """
        # Determine severity
        if days_until <= 7:
            severity = "critical"
        elif days_until <= 30:
            severity = "warning"
        else:
            severity = "info"
        
        # Prepare message
        subject = self._get_alert_subject(license, days_until)
        body = self._get_alert_body(license, days_until)
        
        # Send via email
        if "email" in monitor.alert_methods and monitor.email_addresses:
            for email in monitor.email_addresses:
                await self._send_email(email, subject, body)
        
        # Send via webhook
        if "webhook" in monitor.alert_methods and monitor.webhook_url:
            await self._send_webhook(monitor.webhook_url, license, days_until)
        
        # Log alert sent
        alert_record = LicenseAlertSent(
            monitor_id=monitor.id,
            license_id=license.id,
            alert_type="expiring_soon" if days_until > 0 else "expired",
            days_until_expiration=days_until,
            severity=severity,
            message_subject=subject,
            message_body=body,
            sent_via=",".join(monitor.alert_methods),
            sent_to=",".join(monitor.email_addresses or []),
            delivery_status="sent"
        )
        self.db.add(alert_record)
        self.db.commit()
        
        logger.info(f"Sent alert for license {license.license_number} ({days_until} days)")
    
    async def _send_status_change_alert(
        self,
        monitor: LicenseMonitor,
        license: ProfessionalLicense
    ):
        """
        Send alert when license status changes
        """
        subject = f"🚨 URGENT: License Status Changed - {license.license_number}"
        body = f"""
        License status has changed:
        
        License: {license.license_number}
        State: {license.state_code}
        New Status: {license.status.upper()}
        
        Action Required: Review this license immediately.
        """
        
        # Send notifications
        if "email" in monitor.alert_methods and monitor.email_addresses:
            for email in monitor.email_addresses:
                await self._send_email(email, subject, body)
        
        if "webhook" in monitor.alert_methods and monitor.webhook_url:
            await self._send_webhook(
                monitor.webhook_url,
                license,
                days_until=0,
                event="status_change"
            )
    
    def _get_alert_subject(self, license: ProfessionalLicense, days_until: int) -> str:
        """Generate email subject line"""
        if days_until <= 0:
            return f"🚨 EXPIRED: License {license.license_number} has expired"
        elif days_until <= 7:
            return f"⚠️ URGENT: License {license.license_number} expires in {days_until} days"
        else:
            return f"📅 Reminder: License {license.license_number} expires in {days_until} days"
    
    def _get_alert_body(self, license: ProfessionalLicense, days_until: int) -> str:
        """Generate email body"""
        professional_name = f"{license.first_name} {license.last_name}" if license.first_name else "Professional"
        
        if days_until <= 0:
            urgency = "EXPIRED - Immediate action required"
        elif days_until <= 7:
            urgency = "URGENT - Renew immediately"
        else:
            urgency = "Action needed soon"
        
        return f"""
        {urgency}
        
        Professional: {professional_name}
        License: {license.state_code} #{license.license_number}
        Type: {license.license_type}
        Expires: {license.expiration_date}
        Days Remaining: {days_until}
        
        Action Required:
        {"Ensure this professional renews their license immediately." if days_until <= 7 else "Remind professional to renew before expiration."}
        
        ---
        You're receiving this because you're monitoring this license on SkillLedger.
        Manage monitoring: https://skilledger.com/monitoring
        """
    
    async def _send_email(self, to_email: str, subject: str, body: str):
        """
        Send email via SendGrid
        """
        try:
            # TODO: Implement SendGrid integration
            logger.info(f"Email sent to {to_email}: {subject}")
            # For now, just log
            # In production, use SendGrid API:
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
    
    async def _send_webhook(
        self,
        webhook_url: str,
        license: ProfessionalLicense,
        days_until: int,
        event: str = "expiring_soon"
    ):
        """
        Send webhook notification
        """
        try:
            payload = {
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "critical" if days_until <= 7 else "warning",
                "professional": {
                    "name": f"{license.first_name} {license.last_name}",
                },
                "license": {
                    "license_id": license.id,
                    "license_number": license.license_number,
                    "state": license.state_code,
                    "type": license.license_type,
                    "status": license.status,
                    "expires": license.expiration_date.isoformat(),
                    "days_until_expiration": days_until
                },
                "alert": {
                    "message": f"License expires in {days_until} days",
                    "action_required": "Remind professional to renew"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                
            logger.info(f"Webhook sent to {webhook_url}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook to {webhook_url}: {str(e)}")
