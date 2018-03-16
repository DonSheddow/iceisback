import requests
import config

def send_mail(subject, body):
    auth = ("api", config.MAILGUN_API_KEY)
    data = {"from": config.MAIL_FROM,
             "to": [config.MAIL_TO],
             "subject": subject,
             "text": body}

    r = requests.post(
        config.MAILGUN_API_URL,
        auth=auth,
        data=data)
    r.raise_for_status()
    return r

def mail_daemon(queue):
    while True:
        try:
            msg = queue.get()
            send_mail(msg['subject'], msg['body'])
        except Exception as e:
            print("Unable to send email: ", e)
