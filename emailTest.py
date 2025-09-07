import smtplib
from email.message import EmailMessage

def send_email(to_address, subject, body, from_address, password):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_address
    msg.set_content(body)

    with smtplib.SMTP_SSL('mailservices.uwaterloo.ca', 465) as smtp:
        smtp.login(from_address, password)
        smtp.send_message(msg)

if __name__ == "__main__":
    send_email("b27dai@uwaterloo.ca", "Test Subject", "Test Body", "b27dai@uwaterloo.ca", "Da!20040327")