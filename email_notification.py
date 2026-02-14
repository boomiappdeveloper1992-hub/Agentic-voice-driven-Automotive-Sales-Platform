"""
email_notification.py - SendGrid Email Integration
Sends confirmation emails for test drive bookings and appointments
"""

import os
import logging
import requests
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """
    Email notification service using SendGrid API
    
    Features:
    - Test drive confirmations
    - Appointment confirmations
    - Rescheduling notifications
    - Cancellation notices
    """
    
    def __init__(self, api_key: Optional[str] = None, from_email: Optional[str] = None):
        """
        Initialize email service
        
        Args:
            api_key: SendGrid API key (or set SENDGRID_API_KEY env var)
            from_email: Sender email (or set SENDER_EMAIL env var)
        """
        ##self.api_key = api_key or os.getenv('SENDGRID_API_KEY')
        self.api_key = 'XXXXXXXXXXXXXXXXXXXXX'
        ##self.from_email = from_email or os.getenv('SENDER_EMAIL', 'XXXXXXXXXXXXX@gmail.com')
        self.from_email = 'XXXXXXXX@gmail.com'
        self.api_url = 'https://XXXXX.com/v3/mail/send'
        
        if not self.api_key:
            logger.warning("⚠️ SendGrid API key not configured. Email notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"✅ Email service initialized. Sender: {self.from_email}")
    
    def _send_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> Dict:
        """
        Internal method to send email via SendGrid API
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML version of email
            text_content: Plain text version
            
        Returns:
            Dict with success status and message
        """
        if not self.enabled:
            logger.warning(f"📧 Email service disabled. Would send to: {to_email}")
            return {
                'success': False,
                'message': 'Email service not configured'
            }
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}],
                        "subject": subject
                    }
                ],
                "from": {"email": self.from_email},
                "content": [
                    {
                        "type": "text/plain",
                        "value": text_content
                    },
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            logger.info(f"📤 Sending email to: {to_email}")
            logger.info(f"   Subject: {subject}")
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info(f"✅ Email sent successfully to {to_email}")
                return {
                    'success': True,
                    'message': 'Email sent successfully'
                }
            else:
                logger.error(f"❌ SendGrid API error: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return {
                    'success': False,
                    'message': f'Failed to send email: {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            logger.error("❌ Email send timeout")
            return {
                'success': False,
                'message': 'Email send timeout'
            }
        except Exception as e:
            logger.error(f"❌ Email send error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def send_test_drive_confirmation(self, booking_data: Dict) -> Dict:
        """
        Send test drive booking confirmation email
        
        Args:
            booking_data: Dict containing:
                - customer_email
                - customer_name
                - vehicle_name
                - date
                - time
                - booking_id
                - pickup_location
                
        Returns:
            Dict with success status
        """
        try:
            subject = f"🚗 Test Drive Confirmed - {booking_data['vehicle_name']}"
            
            # HTML email template
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f3f4f6;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 28px;">🎉 Test Drive Confirmed!</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">
                                Get ready to experience your dream car
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; color: #374151; margin: 0 0 20px 0;">
                                Hi <strong>{booking_data['customer_name']}</strong>,
                            </p>
                            
                            <p style="font-size: 16px; color: #374151; margin: 0 0 30px 0;">
                                Your test drive has been successfully booked! We're excited to have you experience this amazing vehicle.
                            </p>
                            
                            <!-- Booking Details Card -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f9fafb; border-radius: 12px; border: 2px solid #e5e7eb;">
                                <tr>
                                    <td style="padding: 25px;">
                                        <h3 style="margin: 0 0 20px 0; color: #111827; font-size: 18px;">
                                            📋 Booking Details
                                        </h3>
                                        
                                        <table width="100%" cellpadding="8" cellspacing="0">
                                            <tr>
                                                <td style="color: #6b7280; font-size: 14px; width: 40%;">
                                                    <strong>🆔 Booking ID:</strong>
                                                </td>
                                                <td style="color: #111827; font-size: 14px;">
                                                    {booking_data['booking_id']}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="color: #6b7280; font-size: 14px;">
                                                    <strong>🚗 Vehicle:</strong>
                                                </td>
                                                <td style="color: #111827; font-size: 14px;">
                                                    {booking_data['vehicle_name']}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="color: #6b7280; font-size: 14px;">
                                                    <strong>📅 Date:</strong>
                                                </td>
                                                <td style="color: #111827; font-size: 14px;">
                                                    {booking_data['date']}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="color: #6b7280; font-size: 14px;">
                                                    <strong>⏰ Time:</strong>
                                                </td>
                                                <td style="color: #111827; font-size: 14px;">
                                                    {booking_data['time']}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="color: #6b7280; font-size: 14px;">
                                                    <strong>📍 Location:</strong>
                                                </td>
                                                <td style="color: #111827; font-size: 14px;">
                                                    {booking_data['pickup_location']}
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Important Reminders -->
                            <div style="margin-top: 30px; padding: 20px; background-color: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 8px;">
                                <h4 style="margin: 0 0 15px 0; color: #1e40af; font-size: 16px;">
                                    📋 Important Reminders
                                </h4>
                                <ul style="margin: 0; padding-left: 20px; color: #1e3a8a;">
                                    <li style="margin-bottom: 8px;">Please arrive <strong>10 minutes early</strong></li>
                                    <li style="margin-bottom: 8px;">Bring your <strong>valid driver's license</strong></li>
                                    <li style="margin-bottom: 8px;">Booking ID: <strong>{booking_data['booking_id']}</strong></li>
                                    <li>Contact us at <strong>+971-4-XXX-XXXX</strong> for any changes</li>
                                </ul>
                            </div>
                            
                            <!-- Call to Action -->
                            <div style="text-align: center; margin-top: 30px;">
                                <a href="https://your-website.com/booking/{booking_data['booking_id']}" 
                                   style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                          color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; 
                                          font-weight: 600; font-size: 16px;">
                                    📱 View Booking Details
                                </a>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 10px 0; color: #6b7280; font-size: 14px;">
                                Thank you for choosing our automotive platform!
                            </p>
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                © 2025 Automotive AI Platform. All rights reserved.
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
            
            # Plain text version
            text_content = f"""
TEST DRIVE CONFIRMED
━━━━━━━━━━━━━━━━━━━━

Hi {booking_data['customer_name']},

Your test drive has been successfully booked!

BOOKING DETAILS:
━━━━━━━━━━━━━━━━━━━━
🆔 Booking ID: {booking_data['booking_id']}
🚗 Vehicle: {booking_data['vehicle_name']}
📅 Date: {booking_data['date']}
⏰ Time: {booking_data['time']}
📍 Location: {booking_data['pickup_location']}

IMPORTANT REMINDERS:
━━━━━━━━━━━━━━━━━━━━
✓ Arrive 10 minutes early
✓ Bring your valid driver's license
✓ Contact us at +971-4-XXX-XXXX for changes

We look forward to seeing you!

Best regards,
Automotive AI Platform Team
"""
            
            return self._send_email(
                to_email=booking_data['customer_email'],
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"❌ Test drive email error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def send_appointment_confirmation(self, appointment_data: Dict) -> Dict:
        """
        Send appointment confirmation email
        
        Args:
            appointment_data: Dict containing appointment details
            
        Returns:
            Dict with success status
        """
        try:
            subject = f"📅 Appointment Confirmed - {appointment_data.get('vehicle', 'Vehicle Inquiry')}"
            
            html_content = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">✅ Appointment Confirmed</h1>
        </div>
        
        <div style="padding: 30px;">
            <p>Hi <strong>{appointment_data['customer_name']}</strong>,</p>
            <p>Your appointment has been confirmed!</p>
            
            <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">📋 Details:</h3>
                <p><strong>ID:</strong> {appointment_data['id']}</p>
                <p><strong>Date:</strong> {appointment_data['date']}</p>
                <p><strong>Time:</strong> {appointment_data['time']}</p>
                <p><strong>Vehicle:</strong> {appointment_data.get('vehicle', 'N/A')}</p>
            </div>
            
            <p>We look forward to seeing you!</p>
        </div>
    </div>
</body>
</html>
"""
            
            text_content = f"""
APPOINTMENT CONFIRMED

Hi {appointment_data['customer_name']},

Your appointment has been confirmed!

DETAILS:
ID: {appointment_data['id']}
Date: {appointment_data['date']}
Time: {appointment_data['time']}
Vehicle: {appointment_data.get('vehicle', 'N/A')}

We look forward to seeing you!

Best regards,
Automotive AI Platform
"""
            
            return self._send_email(
                to_email=appointment_data['customer_email'],
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"❌ Appointment email error: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def send_cancellation_notice(self, email: str, booking_id: str, booking_type: str = "test drive") -> Dict:
        """Send cancellation confirmation"""
        subject = f"🔴 {booking_type.title()} Cancelled - {booking_id}"
        
        html_content = f"""
<div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
    <div style="background: #fee2e2; padding: 30px; border-radius: 8px;">
        <h2>❌ Booking Cancelled</h2>
        <p>Your {booking_type} (ID: <strong>{booking_id}</strong>) has been cancelled.</p>
        <p>You can rebook anytime by visiting our platform.</p>
    </div>
</div>
"""
        
        text_content = f"""
BOOKING CANCELLED

Your {booking_type} (ID: {booking_id}) has been cancelled.

You can rebook anytime by visiting our platform.

Best regards,
Automotive AI Platform
"""
        
        return self._send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# ═══════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════

_email_service = None


def get_email_service() -> EmailNotificationService:
    """Get singleton email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailNotificationService()
    return _email_service
