"""
Email notification system for dog rescue alerts
v1.0.0

Sends notifications for:
- New dogs added
- Status changes on watch list dogs
- High fit score dogs becoming available
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime


# Email configuration - set these as environment variables
EMAIL_CONFIG = {
  "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
  "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
  "sender_email": os.environ.get("SENDER_EMAIL", ""),
  "sender_password": os.environ.get("SENDER_PASSWORD", ""),  # App password for Gmail
  "recipient_emails": os.environ.get("RECIPIENT_EMAILS", "").split(","),
}

# Notification thresholds
MIN_FIT_SCORE_NOTIFY = 5  # Notify for dogs with fit score >= this
NOTIFY_NEW_DOGS = True
NOTIFY_STATUS_CHANGES = True
NOTIFY_WATCH_LIST = True


def is_configured() -> bool:
  """Check if email is properly configured"""
  return bool(EMAIL_CONFIG["sender_email"] and EMAIL_CONFIG["sender_password"])


def should_notify(change: Dict) -> bool:
  """Determine if a change warrants notification"""
  change_type = change.get("change_type", "")
  fit_score = change.get("fit_score", 0) or 0
  watch_list = change.get("watch_list", "") == "Yes"
  
  # Always notify for watch list dogs
  if watch_list and NOTIFY_WATCH_LIST:
    return True
  
  # Notify for new high-fit dogs
  if change_type == "new_dog" and NOTIFY_NEW_DOGS:
    if fit_score >= MIN_FIT_SCORE_NOTIFY:
      return True
  
  # Notify for status changes on high-fit dogs
  if change_type == "status_change" and NOTIFY_STATUS_CHANGES:
    if fit_score >= MIN_FIT_SCORE_NOTIFY:
      return True
    # Always notify when a dog becomes available
    if change.get("new_value", "").lower() == "available":
      return True
  
  return False


def format_notification_email(changes: List[Dict]) -> tuple:
  """Format changes into email subject and body"""
  
  # Categorize changes
  new_dogs = [c for c in changes if c["change_type"] == "new_dog"]
  status_changes = [c for c in changes if c["change_type"] == "status_change"]
  watch_list_changes = [c for c in changes if c.get("watch_list") == "Yes"]
  
  # Build subject
  subject_parts = []
  if watch_list_changes:
    subject_parts.append(f"🔔 {len(watch_list_changes)} Watch List Alert(s)")
  if new_dogs:
    subject_parts.append(f"🆕 {len(new_dogs)} New Dog(s)")
  if status_changes and not watch_list_changes:
    subject_parts.append(f"📢 {len(status_changes)} Status Change(s)")
  
  subject = " | ".join(subject_parts) if subject_parts else "🐕 Dog Rescue Update"
  
  # Build HTML body
  html = """
  <html>
  <head>
    <style>
      body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
      .section {{ margin: 20px 0; padding: 15px; border-radius: 8px; }}
      .watch-list {{ background: #fff3cd; border: 1px solid #ffc107; }}
      .new-dog {{ background: #d4edda; border: 1px solid #28a745; }}
      .status-change {{ background: #cce5ff; border: 1px solid #007bff; }}
      .dog-card {{ margin: 10px 0; padding: 10px; background: white; border-radius: 4px; }}
      .fit-score {{ font-weight: bold; color: #28a745; }}
      .dog-name {{ font-size: 1.2em; font-weight: bold; }}
      h2 {{ margin-top: 0; }}
    </style>
  </head>
  <body>
    <h1>🐕 Dog Rescue Tracker Update</h1>
    <p>Generated: {timestamp}</p>
  """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"))
  
  # Watch list alerts (highest priority)
  if watch_list_changes:
    html += """
    <div class="section watch-list">
      <h2>🔔 Watch List Alerts</h2>
    """
    for change in watch_list_changes:
      html += _format_dog_card(change)
    html += "</div>"
  
  # New dogs
  non_watch_new = [c for c in new_dogs if c.get("watch_list") != "Yes"]
  if non_watch_new:
    html += """
    <div class="section new-dog">
      <h2>🆕 New Dogs</h2>
    """
    for change in non_watch_new:
      html += _format_dog_card(change)
    html += "</div>"
  
  # Status changes
  non_watch_status = [c for c in status_changes if c.get("watch_list") != "Yes"]
  if non_watch_status:
    html += """
    <div class="section status-change">
      <h2>📢 Status Changes</h2>
    """
    for change in non_watch_status:
      html += _format_dog_card(change)
    html += "</div>"
  
  html += """
  <hr>
  <p style="color: #666; font-size: 0.9em;">
    This is an automated notification from your Dog Rescue Tracker.<br>
    To stop receiving these emails, remove your email from the configuration.
  </p>
  </body>
  </html>
  """
  
  return subject, html


def _format_dog_card(change: Dict) -> str:
  """Format a single dog change as HTML card"""
  dog_name = change.get("dog_name", "Unknown")
  rescue = change.get("rescue_name", "")
  fit_score = change.get("fit_score", "?")
  change_type = change.get("change_type", "")
  old_val = change.get("old_value", "")
  new_val = change.get("new_value", "")
  
  # Determine what to show
  if change_type == "new_dog":
    detail = f"New listing: {new_val}"
  elif change_type == "status_change":
    detail = f"Status: {old_val} → <strong>{new_val}</strong>"
  else:
    field = change.get("field_changed", "")
    detail = f"{field}: {old_val} → {new_val}"
  
  return f"""
  <div class="dog-card">
    <span class="dog-name">{dog_name}</span> 
    <span class="fit-score">(Fit: {fit_score})</span><br>
    <span style="color: #666;">{rescue}</span><br>
    {detail}
  </div>
  """


def send_notification(changes: List[Dict]) -> bool:
  """Send email notification for changes"""
  if not is_configured():
    print("  ⚠️ Email not configured - skipping notification")
    print("  Set SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAILS environment variables")
    return False
  
  # Filter to only notifiable changes
  notifiable = [c for c in changes if should_notify(c)]
  
  if not notifiable:
    print("  ℹ️ No changes meet notification threshold")
    return True
  
  subject, html_body = format_notification_email(notifiable)
  
  # Create message
  msg = MIMEMultipart("alternative")
  msg["Subject"] = subject
  msg["From"] = EMAIL_CONFIG["sender_email"]
  msg["To"] = ", ".join(EMAIL_CONFIG["recipient_emails"])
  
  # Attach HTML
  msg.attach(MIMEText(html_body, "html"))
  
  # Send
  try:
    with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
      server.starttls()
      server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
      server.send_message(msg)
    
    print(f"  ✅ Notification sent: {len(notifiable)} updates")
    return True
    
  except Exception as e:
    print(f"  ❌ Failed to send notification: {e}")
    return False


def send_test_email() -> bool:
  """Send a test email to verify configuration"""
  if not is_configured():
    print("❌ Email not configured")
    return False
  
  subject = "🐕 Dog Rescue Tracker - Test Notification"
  html = """
  <html>
  <body>
    <h1>Test Notification</h1>
    <p>If you receive this email, your Dog Rescue Tracker notifications are working!</p>
    <p>Sent: {}</p>
  </body>
  </html>
  """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
  
  msg = MIMEMultipart("alternative")
  msg["Subject"] = subject
  msg["From"] = EMAIL_CONFIG["sender_email"]
  msg["To"] = ", ".join(EMAIL_CONFIG["recipient_emails"])
  msg.attach(MIMEText(html, "html"))
  
  try:
    with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
      server.starttls()
      server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
      server.send_message(msg)
    print("✅ Test email sent successfully!")
    return True
  except Exception as e:
    print(f"❌ Failed to send test email: {e}")
    return False


if __name__ == "__main__":
  send_test_email()
