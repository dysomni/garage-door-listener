import json
import os
import time

import boto3
import urllib3

sqs = boto3.client("sqs")
queue_url = os.environ.get("SQS_QUEUE_URL")
timeout = urllib3.Timeout(connect=2.0, read=7.0)
http = urllib3.PoolManager(timeout=timeout)
pushcut_request_url = os.environ.get("PUSHCUT_REQUEST_URL")

class ExpectedExit(Exception):
    pass

def send_open_garage_request():
    print(f'sending prompt to open garage door now')

    http.request('GET', pushcut_request_url)

def check_tesla_driving():
    body = json.dumps(
        {
            "scope": "openid email offline_access",
            "refresh_token": os.environ.get("TESLA_REFRESH_TOKEN"),
            "client_id": "ownerapi",
            "grant_type": "refresh_token",
        }
    )
    response = http.request(
        "POST",
        "https://auth.tesla.com/oauth2/v3/token",
        body=body,
        headers={"Content-Type": "application/json"},
    )
    if response.status != 200:
        print(response.data)
        raise Exception(
            f"Request to grab tesla access token failed with a status code of {response.status}."
        )
    decoded = response.data.decode()
    data = json.loads(decoded)
    access_token = data["access_token"]
    response = http.request(
        "GET",
        "https://owner-api.teslamotors.com/api/1/vehicles/1492685645785570/data_request/drive_state",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    )
    if response.status != 200:
        print(f'request to get tesla driving state failed.')
        print(response.data)
        raise Exception(
            f"Request to grab tesla driving state failed with a status code of {response.status}."
        )

    decoded = response.data.decode()
    data = json.loads(decoded)
    shift_state = data["response"]["shift_state"]
    latitude = data["response"]["latitude"]
    longitude = data["response"]["longitude"]
    if shift_state != "D":
        raise Exception("Tesla is not currently driving.")
    if not (
        (28.093083387712372 < latitude < 28.09519491177466)
        and (-82.5173913339998 < longitude < -82.51368426536229)
    ):
        raise Exception("Tesla is not in range of the house.")


def send_pushover_message(message):
    http.request(
        "POST",
        "https://api.pushover.net/1/messages.json",
        fields={
            "token": os.environ.get("PUSHOVER_TOKEN"),
            "user": os.environ.get("PUSHOVER_USER"),
            "message": message,
            "priority": 0,
        },
    )


def send_open_garage_command():
    return sqs.send_message(
        MessageGroupId="cool",
        MessageDeduplicationId=str(time.time()),
        QueueUrl=queue_url,
        DelaySeconds=0,
        MessageBody=json.dumps({"command": "open"}),
    )


def lambda_handler(event, context):
    # TODO implement
    authorization = event.get("headers", {}).get("authorization", "bad")
    if os.environ.get("AUTH") == authorization:
        try:
            check_tesla_driving()
            response = send_open_garage_command()
            send_pushover_message("Garage has been opened.")
        except Exception as e:
            try:
                # send_pushover_message(f"Cannot send request to open garage: {e}")
                send_open_garage_request()
            except Exception as e:
                print(e)
                return {"statusCode": 500, "body": str(e)}
            print(e)
            return {"statusCode": 200, "body": str(e)}

        print("success")
        return {"statusCode": 200, "body": json.dumps(response)}

    return {"statusCode": 404, "body": "not found"}
