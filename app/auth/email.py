import sendgrid
import os
from flask import current_app
from sendgrid.helpers.mail import *


def auth_email(from_email, subject, to_email, content):
    sg = sendgrid.SendGridAPIClient(
        apikey=current_app.config['SENDGRID_API_KEY'])
    from_email = Email("justfiles-verify@davidcrandall.com")
    to_email = Email(to_email)
    content = Content("text/html", content)
    mail = Mail(from_email, subject, to_email, content)
    response = sg.client.mail.send.post(request_body=mail.get())

    return response.status_code


def reset_email(from_email, subject, to_email, content):
    sg = sendgrid.SendGridAPIClient(
        apikey=current_app.config['SENDGRID_API_KEY'])
    from_email = Email("justfiles-reset@davidcrandall.com")
    to_email = Email(to_email)
    content = Content("text/html", content)
    mail = Mail(from_email, subject, to_email, content)
    response = sg.client.mail.send.post(request_body=mail.get())

    return response.status_code
