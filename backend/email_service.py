import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime
import pytz
from typing import List
import database
import aiosqlite

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADELAIDE_TZ = pytz.timezone('Australia/Adelaide')

# Security Note: In a production environment, email credentials should be encrypted
# before storage in the database and decrypted when needed. This implementation
# stores credentials in plaintext for simplicity, but production deployments should
# implement proper encryption mechanisms.

async def get_active_email_config():
    """Get the active email configuration from the database."""
    configs = await database.get_email_configs()
    if configs:
        # For now, we'll use the first config as active
        # In the future, we might want to mark one as active
        return configs[0]
    return None

def send_email_with_config(config: dict, recipients: List[str], subject: str, body: str, attachments: List[str] = None):
    """
    Send an email using the provided configuration.
    
    Args:
        config: Email configuration dictionary
        recipients: List of recipient email addresses
        subject: Email subject
        body: Email body content
        attachments: List of file paths to attach
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{config.get('sender_name', 'Cerberus AI')} <{config['sender_email']}>"
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'html'))
        
        # Add attachments if any
        if attachments:
            for file_path in attachments:
                if os.path.isfile(file_path):
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(file_path)}'
                    )
                    msg.attach(part)
        
        # Create SMTP session
        if config['use_ssl']:
            server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'])
        else:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            if config['use_tls']:
                server.starttls()
        
        # Login and send email
        server.login(config['username'], config['password'])
        text = msg.as_string()
        server.sendmail(config['sender_email'], recipients, text)
        server.quit()
        
        logger.info(f"Email sent successfully to {', '.join(recipients)}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

async def send_scheduled_research_email(research_config: dict, research_result: str):
    """
    Send scheduled research results via email.
    
    Args:
        research_config: Scheduled research configuration
        research_result: The research result content to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get email configuration
        email_config = await get_active_email_config()
        if not email_config:
            logger.error("No email configuration found")
            return False
        
        # Get recipient group and recipients
        recipient_group_id = research_config['recipient_group_id']
        recipients = await database.get_email_recipients(recipient_group_id)
        if not recipients:
            logger.warning(f"No recipients found for group ID {recipient_group_id}")
            return False
        
        # Extract email addresses
        recipient_emails = [recipient['email'] for recipient in recipients]
        
        # Create email content
        subject = f"Scheduled Threat Research Report: {research_config['name']}"
        
        # Format the email body with HTML
        body = f"""<html>
<body>
    <h2>Scheduled Threat Research Report</h2>
    <p><strong>Report Name:</strong> {research_config['name']}</p>
    <p><strong>Generated at:</strong> {datetime.now(ADELAIDE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
    <hr>
    <h3>Research Results:</h3>
    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
        {research_result.replace(chr(10), "<br>")}
    </div>
    <hr>
    <p><em>This is an automated report from Cerberus AI.</em></p>
</body>
</html>"""
        
        # Send email
        success = send_email_with_config(email_config, recipient_emails, subject, body)
        
        # Log the delivery
        await database.add_email_delivery_log(
            scheduled_research_id=research_config['id'],
            subject=subject,
            recipients=recipient_emails,
            status="sent" if success else "failed",
            sent_at=datetime.now(ADELAIDE_TZ),
            error_message=None if success else "Failed to send email"
        )
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send scheduled research email: {str(e)}")
        # Log the delivery failure
        try:
            recipient_group_id = research_config['recipient_group_id']
            recipients = await database.get_email_recipients(recipient_group_id)
            recipient_emails = [recipient['email'] for recipient in recipients] if recipients else []
            
            await database.add_email_delivery_log(
                scheduled_research_id=research_config['id'],
                subject=f"Scheduled Threat Research Report: {research_config['name']}",
                recipients=recipient_emails,
                status="failed",
                sent_at=datetime.now(ADELAIDE_TZ),
                error_message=str(e)
            )
        except Exception as log_error:
            logger.error(f"Failed to log email delivery failure: {str(log_error)}")
        
        return False