import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# You can load these from environment variables for security
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "codingpirates70@example.com")
SMTP_PASS = os.getenv("SMTP_PASS")

def send_confirmation_email(to_email: str, username: str, complaint_id: str):
    subject = "🛡️ Complaint Registered Successfully - CyVox"
    body = f"""
    <html>
    <body>
        <p>Dear {username},</p>
        <p>Thank you for reporting the cyber fraud incident.</p>
        <p>Your complaint has been successfully registered with the following ID:</p>
        <h3>{complaint_id}</h3>
        <p>We will analyze and match the audio against our scammer database and update you if a match is found.</p>
        <br>
        <p>Regards,<br>CyVox Support Team</p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        print(f"📧 Confirmation email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
