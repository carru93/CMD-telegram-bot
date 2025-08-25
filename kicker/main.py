import json, os
import urllib3
import boto3


BOT_TOKEN = os.environ["BOT_TOKEN"]
QUEUE_URL = os.environ["QUEUE_URL"]
TABLE_NAME = os.environ["TABLE_NAME"]

http = urllib3.PoolManager()
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def tg_call(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    resp = http.request('POST', url, body=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'})
    data = json.loads(resp.data.decode('utf-8'))
    if not data.get('ok'):
        raise RuntimeError(f"{method} failed: {data}")
    return data['result']

def delete_verification_message(user_id, chat_id):
    resp = table.get_item(Key={'user_id': user_id, 'chat_id': chat_id})
    item = resp.get("Item")
    if item is None: return
    verification_message_id=item.get('verification_message')

    data = {
        "chat_id": chat_id,
        "message_id": int(verification_message_id)
    }
    tg_call("deleteMessage", data)

def delete_entry(user_id, chat_id):
    print(f"Deleting entry on dynamoDB")
    return table.delete_item(Key={'user_id': user_id, 'chat_id': chat_id})

def ban_user(user_id, chat_id):
    data = {
        "chat_id": chat_id,
        "user_id": user_id,
        "revoke_messages": True
    }
    tg_call("banChatMember", data)

def sqs_handler(event, context):
    try:
        for record in event['Records']:
            payload = json.loads(record['body'])
            user_id = payload['user_id']
            chat_id = payload['chat_id']

            resp = table.get_item(Key={'user_id': user_id, 'chat_id': chat_id})
            item = resp.get("Item")
            if item:
                ban_user(user_id, chat_id)
                delete_verification_message(user_id, chat_id)
                delete_entry(user_id, chat_id)
    except Exception as e:
        print(e)
        return { 'statusCode': 200, 'body': json.dumps('An arror has been thrown') }
