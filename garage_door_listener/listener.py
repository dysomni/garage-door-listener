import json
import os

import boto3
import homescript

CONFIG = os.environ

class Digit(int):
    def isdigit(self):
        return True

def start():
    sqs = boto3.client('sqs')
    queue_url = CONFIG.get('SQS_QUEUE_URL')
    while True:
        try:
            response: dict = sqs.receive_message(
                QueueUrl=queue_url,
                AttributeNames=[
                    'SentTimestamp'
                ],
                MaxNumberOfMessages=10,
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=60,
                WaitTimeSeconds=20
            )

            messages = response.get('Messages', [])
            if not messages:
                print('no messages')
                continue

            for message in messages:
                receipt_handle = message.get('ReceiptHandle')
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle
                )

            message = messages[0]

            command = json.loads(message.get('Body', '{}')).get('command', 'none')
            print("command:", command)

            if command == 'open':
                hs = homescript.HomeScript(CONFIG.get('HOMEBRIDGE_HOST'), CONFIG.get('HOMEBRIDGE_PORT'), CONFIG.get('HOMEBRIDGE_AUTH'))
                hs.getAccessories()
                hs.selectAccessory('controls_gdo_open')
                hs.printSelectedItems()
                hs.setStates(Digit(1))

            # Delete received message from queue

            print('Received and deleted message: %s' % message)
        except Exception as e:
            print('ERROR', str(e))
