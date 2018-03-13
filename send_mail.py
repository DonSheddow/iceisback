import traceback
import sys
import json
import requests
import pika
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


def callback(ch, method, props, body):
    try:
        msg = json.loads(body)
        send_mail(msg['subject'], msg['body'])
    except:
        print(traceback.format_exc())


if __name__ == '__main__':
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue=config.QUEUE_NAME)

    channel.basic_consume(callback,
                          queue=config.QUEUE_NAME,
                          no_ack=True)

    channel.start_consuming()
