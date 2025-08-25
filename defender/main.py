import json, os, random, time
import urllib3
import boto3

BOT_TOKEN = os.environ["BOT_TOKEN"]
QUEUE_URL = os.environ["QUEUE_URL"]
TABLE_NAME = os.environ["TABLE_NAME"]

http = urllib3.PoolManager()
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)
sqs = boto3.client('sqs')

# Util functions #
def generateNumber():
    return random.randint(1, 99)

def generateSecNumbers():
    n1 = generateNumber()
    n2 = generateNumber()
    return (n1, n2, n1+n2)

# Telegram Helpers #
def tg_call(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    resp = http.request('POST', url, body=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'})
    data = json.loads(resp.data.decode('utf-8'))
    if not data.get('ok'):
        raise RuntimeError(f"{method} failed: {data}")
    return data['result']

def send_message(chat_id, message, **kwargs):
    payload = { "chat_id": chat_id, "text": message, **kwargs }
    return tg_call("sendMessage", payload)

def answer_callback_query(cb_id, text=None, show_alert=False):
    payload = {"callback_query_id": cb_id}
    if text is not None:
        payload["text"] = text
    if show_alert:
        payload["show_alert"] = True
    return tg_call("answerCallbackQuery", payload)

def delete_message(chat_id, message_id):
    payload = { "chat_id": chat_id, "message_id": message_id }
    return tg_call("deleteMessage", payload)

def restrict_user(chat_id, user_id):
    perms = {"can_send_messages": False, "can_send_audios": False, "can_send_documents": False,
             "can_send_photos": False, "can_send_videos": False, "can_send_video_notes": False,
             "can_send_voice_notes": False, "can_send_polls": False,
             "can_send_other_messages": False, "can_add_web_page_previews": False}
    return tg_call("restrictChatMember", { "chat_id": chat_id, "user_id": user_id, "permissions": perms })

def unrestrict_user(chat_id, user_id):
    perms = {"can_send_messages": True, "can_send_audios": True, "can_send_documents": True,
             "can_send_photos": True, "can_send_videos": True, "can_send_video_notes": True,
             "can_send_voice_notes": True, "can_send_polls": True,
             "can_send_other_messages": True, "can_add_web_page_previews": True}
    return tg_call("restrictChatMember", { "chat_id": chat_id, "user_id": user_id, "permissions": perms })

def send_verification_message(chat_id, message, correct_sum):
    wrong_button1 = generateSecNumbers()[2]
    wrong_button2 = generateSecNumbers()[2]

    buttons = [
        { "text": str(wrong_button1), "callback_data": wrong_button1 },
        { "text": str(wrong_button2), "callback_data": wrong_button2 },
        { "text": str(correct_sum), "callback_data": correct_sum },
    ]

    random.shuffle(buttons)
    return send_message(chat_id, message, disable_notification=True, reply_markup={"inline_keyboard": [buttons]})

# Dynamo Helpers #
def save_answer(chat_id, user_id, number, verification_message):
    message_id = verification_message['message_id']
    table.put_item(
        Item={
            'user_id': user_id,
            'chat_id': chat_id,
            'number': number,
            'verification_message': message_id,
            "expires_at": int(time.time()) + 180
        }
    )

def retrieve_correct_number(chat_id, user_id):
    resp = table.get_item(Key={'user_id': user_id, 'chat_id': chat_id})
    item = resp.get("Item")
    return item

def delete_entry(chat_id, user_id):
    return table.delete_item(Key={'user_id': user_id, 'chat_id': chat_id})

# SQS Helpers #
def enqueue_kick(chat_id, user_id, delay=120):
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        DelaySeconds=delay,
        MessageBody=json.dumps({"user_id": user_id, "chat_id": chat_id})
    )

# Lambda handler #
def handle_new_members(message):
    chat = message["chat"]
    chat_id = chat["id"]
    new_members = message.get("new_chat_members", [])

    for user in new_members:
        user_name = user['username']
        user_id = user['id']

        correct_n1, correct_n2, correct_sum = generateSecNumbers()
        reply_message = f"Ciao @{user_name}! Per verificare che tu non sia un bot, quanto fa {correct_n1}+{correct_n2}?"

        sent_message = send_verification_message(chat_id, reply_message, correct_sum)
        save_answer(chat_id, user_id, correct_sum, sent_message)
        enqueue_kick(chat_id, user_id)
        try:
            restrict_user(chat_id, user_id)
        except Exception:
            print("Error restricting user, probably the bot does not have this permition")


def handle_callback(event):
    pressed_value = int(event['data'])
    chat_id = event['message']['chat']['id']
    user = event['from']
    user_id = user['id']
    cb_id = event['id']
    ret_item = retrieve_correct_number(chat_id, user_id)

    if ret_item is None:
        answer_callback_query(cb_id, "Questa verifica non è per te o è scaduta")
        return

    correct_number = int(ret_item['number'])
    if pressed_value == correct_number:
        answer_callback_query(cb_id, "Verifica superata✅")
    else:
        answer_callback_query(cb_id, f"Il numero corretto era {correct_number}... Per questa volta passi...")
        pass

    try:
        unrestrict_user(chat_id, user_id)
    except Exception:
        pass
    delete_message(chat_id, int(ret_item['verification_message']))
    delete_entry(chat_id, user['id'])

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])

        if "callback_query" in body:
            handle_callback(body['callback_query'])
        elif "message" in body:
            msg = body["message"]
            if msg.get("chat", {}).get("type") in ("group", "supergroup") and "new_chat_members" in msg:
                handle_new_members(msg)

        return { 'statusCode': 200, 'body': json.dumps('ok') }

    except Exception as e:
        print(e)
        return { 'statusCode': 200, 'body': json.dumps('An arror has been thrown') }

