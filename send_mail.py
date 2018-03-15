import requests
import config

def send_mail(subject, body):
    auth = ("api", config.MAILGUN_API_KEY)
    data = {"from": config.MAIL_FROM,
             "to": [config.MAIL_TO],
             "subject": subject,
             "text": body}

    return requests.post(
        config.MAILGUN_API_URL,
        auth=auth,
        data=data)

def mail_daemon(queue):
    while True:
        msg = queue.get()
        send_mail(msg['subject'], msg['body'])
