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
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.footnote import footnote_plugin

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADELAIDE_TZ = pytz.timezone('Australia/Adelaide')

# Security Note: In a production environment, email credentials should be encrypted
# before storage in the database and decrypted when needed. This implementation
# stores credentials in plaintext for simplicity, but production deployments should
# implement proper encryption mechanisms.

async def get_specific_email_config(config_id: int):
    """Get a specific email configuration by ID from the database."""
    configs = await database.get_email_configs()
    for config in configs:
        if config['id'] == config_id:
            return config
    return None

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

async def send_scheduled_research_email(research_config: dict, research_result: str, test_email: str = None, email_config_id: int = None, date_range_start: str = None, date_range_end: str = None):
    """
    Send scheduled research results via email.
    
    Args:
        research_config: Scheduled research configuration
        research_result: The research result content to send
        test_email: Optional email address to send to instead of the group
        email_config_id: Optional specific email configuration ID to use
        date_range_start: Start date of the research period (for display in email and logs)
        date_range_end: End date of the research period (for display in email and logs)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get email configuration
        email_config = None
        
        # If a specific email config ID is provided, use it
        if email_config_id:
            email_config = await get_specific_email_config(email_config_id)
        else:
            # Otherwise, use the active/default email configuration
            email_config = await get_active_email_config()
        if not email_config:
            logger.error("No email configuration found")
            return False
        
        # Get recipient group and recipients
        recipient_emails = []
        
        # If test_email is provided, use it instead of the group
        if test_email:
            recipient_emails = [test_email]
        else:
            # If no test_email, we must have a recipient group
            recipient_group_id = research_config.get('recipient_group_id')
            if not recipient_group_id:
                logger.error("No recipient group ID provided and no test email specified")
                return False
                
            recipients = await database.get_email_recipients(recipient_group_id)
            if not recipients:
                logger.warning(f"No recipients found for group ID {recipient_group_id}")
                return False
            
            # Extract email addresses
            recipient_emails = [recipient['email'] for recipient in recipients]
        
        # Create email content
        subject = f"Scheduled Threat Research Report: {research_config['name']}"
        
        # Convert markdown to HTML
        md = MarkdownIt("commonmark", {"breaks": True, "html": True})
        md_result = md.render(research_result)
        
        # Format the email body with HTML
        body = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #22c55e;">Scheduled Threat Research Report</h2>
    <p><strong>Report Name:</strong> {research_config['name']}</p>
    <p><strong>Description:</strong> {research_config.get('description', 'N/A')}</p>
    <p><strong>Research Period:</strong> {date_range_start or 'N/A'} to {date_range_end or 'N/A'}</p>
    <p><strong>Generated at:</strong> {datetime.now(ADELAIDE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
    <hr style="border: 1px solid #ddd;">
    <h3 style="color: #22c55e;">Research Results:</h3>
    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; border-left: 4px solid #22c55e;">
        {md_result}
    </div>
    <hr style="border: 1px solid #ddd;">
    <p><em>This is an automated report from Cerberus AI.</em></p>
</body>
</html>"""
        
        # Send email
        success = send_email_with_config(email_config, recipient_emails, subject, body)
        
        # Log the delivery
        await database.add_email_delivery_log(
            scheduled_research_id=research_config.get('id', 0),  # Use 0 for test emails
            subject=subject,
            recipients=recipient_emails,
            status="sent" if success else "failed",
            sent_at=datetime.now(ADELAIDE_TZ),
            error_message=None if success else "Failed to send email",
            date_range_start=date_range_start,
            date_range_end=date_range_end
        )
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send scheduled research email: {str(e)}")
        # Log the delivery failure
        try:
            recipient_emails = [test_email] if test_email else []
            if not test_email:
                recipient_group_id = research_config.get('recipient_group_id')
                if recipient_group_id is not None and recipient_group_id != 0:
                    recipients = await database.get_email_recipients(recipient_group_id)
                    recipient_emails = [recipient['email'] for recipient in recipients] if recipients else []
            
            await database.add_email_delivery_log(
                scheduled_research_id=research_config.get('id', 0),
                subject=f"Scheduled Threat Research Report: {research_config.get('name', 'Unknown')}",
                recipients=recipient_emails,
                status="failed",
                sent_at=datetime.now(ADELAIDE_TZ),
                error_message=str(e),
                date_range_start=date_range_start,
                date_range_end=date_range_end
            )
        except Exception as log_error:
            logger.error(f"Failed to log email delivery failure: {str(log_error)}")
        
        return False