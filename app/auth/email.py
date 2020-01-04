from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import current_app


def auth_email(_from_email, _subject, _to_email, _content):
    message = Mail(
        from_email=_from_email,
        to_emails=_to_email,
        subject=_subject,
        html_content=_content
    )
    try:
        sg = SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        return response.status_code
    except Exception as e:
        print(str(e))


def reset_email(_from_email, _subject, _to_email, _content):
    message = Mail(
        from_email=_from_email,
        to_emails=_to_email,
        subject=_subject,
        html_content=_content
    )
    try:
        sg = SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        return response.status_code
    except Exception as e:
        print(str(e))
