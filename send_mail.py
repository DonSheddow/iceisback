import sys
from datetime import datetime
from queue import Empty
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
    accumulated_mail = []
    last_mail = datetime.min
    while True:
        try:
            msg = queue.get(timeout=1)
            accumulated_mail.append(msg)
        except Empty:
            pass

        if not accumulated_mail or (datetime.now() - last_mail).seconds < config.MAIL_RATELIMIT:
            continue

        if len(accumulated_mail) == 1:
            msg = accumulated_mail.pop()
            subject = "Received DNS request from {ip}".format(ip=msg['ip'])
            body = "{ip} tried to resolve {domain} at {time} server time".format(
                ip=msg['ip'],
                domain=msg['domain'],
                time=msg['time'])
        else:
            subject = "Received DNS requests"
            body = ""
            for msg in accumulated_mail:
                body += "{ip} tried to resolve {domain} at {time} server time\n".format(
                    ip=msg['ip'],
                    domain=msg['domain'],
                    time=msg['time'])
            accumulated_mail = []

        try:
            send_mail(subject, body)
            last_mail = datetime.now()
        except Exception as e:
            print("Unable to send email: ", e, flush=True, file=sys.stderr)
