"""
Send the jobs-data.xlsx dataset via Gmail SMTP.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SENDER = "charliesheiner@gmail.com"
APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

RECIPIENTS = [
    "alfred.romann@deltaanalysis.com",
    "ross.obrien@deltaanalysis.com",
    "sshaikh@ergo.net",
]

SUBJECT = "AI & Labor Data"

BODY = """\
Hi Alfred, Ross, and Sami,

Attached is the updated AI Labor Analysis dataset (jobs-data.xlsx).

Summary:
- 501 job titles covering 446 unique SOC codes
- 20 industries (NAICS-based) x 17 business functions (SOC-based)
- ~3,855 tasks with Time_Share weighting
- BLS NIOEM employment matrix (67 industry codes, no overlap)
- ~90,000K workers represented (86% sector coverage; remainder is blue-collar roles in goods-producing sectors)

Tabs:
  1A Industries (76 NAICS codes across 20 industries)
  1A Summary (20-industry rollup)
  1B Functions (393 SOC-to-function mappings)
  2 Jobs (501 job titles with BLS data + top-3 industry subsegments)
  2B Job_Industry (SOC x Industry employment pivot)
  3 Tasks (task decomposition with Time_Share, Economy_Weight)
  Matrix (17 functions x 20 industries, raw + normalized)
  Staffing Patterns (6,034 rows)
  Lookup tables + ReadMe

Yellow-highlighted Automatability_Score columns will be filled out by us.

Have a great night!

Best,
Charlie
"""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ATTACHMENT = os.path.join(BASE_DIR, "jobs-data.xlsx")


def send():
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = ", ".join(RECIPIENTS)
    msg['Subject'] = SUBJECT
    msg.attach(MIMEText(BODY, 'plain'))

    # Attach the Excel file
    with open(ATTACHMENT, 'rb') as f:
        part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="jobs-data.xlsx"')
    msg.attach(part)

    # Send via Gmail SMTP
    print(f"Connecting to {SMTP_HOST}:{SMTP_PORT}...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER, APP_PASSWORD)
        server.send_message(msg)

    print(f"Email sent successfully!")
    print(f"  From: {SENDER}")
    print(f"  To: {', '.join(RECIPIENTS)}")
    print(f"  Subject: {SUBJECT}")
    print(f"  Attachment: {os.path.basename(ATTACHMENT)} ({os.path.getsize(ATTACHMENT)/1024:.0f} KB)")


if __name__ == "__main__":
    send()
