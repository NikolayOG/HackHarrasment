from django.http import HttpResponse
import json

from sklearn.feature_extraction.text import TfidfVectorizer

from HackHarrassmentApp.services.DetectionService import DetectionService
from HackHarrassmentApp.services.Model import Model
from HackHarrassmentApp.services.ReaderService import ReaderService
from HackHarrassmentApp.services.ChatService import ChatService
from HackHarrassmentApp.services.TwilioService import TwilioService

tfidf_vect = TfidfVectorizer()
model = Model(tfidf_vect)
model.clean()
detection_service = DetectionService(model.get_model(), model.get_svm(), tfidf_vect)
reader = ReaderService()
chat_service = ChatService()
twilio_service = TwilioService()


def index(request):
    return HttpResponse(detection_service.is_harrassment(request.POST.get("txt")))

def create_user(request):
    user = "".join(request.POST.get("name").split())
    if user is None:
        return HttpResponse('User name not set')
    return HttpResponse(chat_service.add_user(user))


def get_relations(request):
    relations = chat_service.get_all_relations()
    return HttpResponse(json.dumps(relations))


def get_users(request):
    after = request.GET.get('user_id', 0)
    users = chat_service.get_all_users_after(after)
    user_data = []
    for user in users:
        user_data.append({
            'id': user[0],
            'name': user[1],
            'tagged': user[2]
        })
    return HttpResponse(json.dumps(user_data))


def get_latest_messages(request):
    row_id = request.GET.get('last_msg')
    if row_id is None:
        return HttpResponse(chat_service.get_last_message_id())
    result = chat_service.get_messages_after(row_id)
    messages = []
    for message in result:
        messages.append({
            'id': message[0],
            'sender': message[1],
            'receiver': message[2],
            'msg': message[3]
        })
    return HttpResponse(json.dumps(messages))


def last_messages(request):
    result = chat_service.latest_messages()
    messages = []
    for message in result:
        messages.append({
            'id': message[0],
            'sender': message[1],
            'receiver': message[2],
            'msg': message[3]
        })
    return HttpResponse(json.dumps(messages))


def post_message(request):
    sender = request.POST.get('sender')
    message = request.POST.get('message')

    if sender is None:
        return HttpResponse('Sender not defined')
    if message is None:
        return HttpResponse('Message not defined')

    if chat_service.user_exists(sender) is None:
        return HttpResponse('That user does not exist')

    str_data = str.split(message)

    if len(str_data) < 2:
        return HttpResponse("Invalid message")

    receiver = str_data[0]
    message = ' '.join(str_data[1:])

    if receiver[:1] != '@' and receiver[:1] != '+':
        return HttpResponse("Invalid receiver")
    if receiver[:1] == '+':
        is_phone = True
    else:
        is_phone = False
    if is_phone is False:
        receiver = receiver[1:]

    if chat_service.user_exists(receiver) is None:
        return HttpResponse('Receiver does not exist')

    print(is_phone)

    if is_phone is True:
        twilio_service.send_sms(receiver, message)

    is_tagged = detection_service.is_harrassment(message)
    row_id = chat_service.insert_message(sender, receiver, message)

    if is_tagged == 1:
        chat_service.set_user_tagged(sender)

    response = {
        'id': row_id,
        'tagged': is_tagged
    }

    return HttpResponse(json.dumps(response))


def on_incoming_sms(request):
    print(request.POST)

    sender = request.POST.get('From')
    message = request.POST.get('Body')

    if sender is None or message is None:
        return HttpResponse()

    if sender is None:
        return HttpResponse()
    if message is None:
        return HttpResponse()

    str_data = str.split(message)

    chat_service.add_user(sender)

    if len(str_data) < 2:
        return HttpResponse()

    receiver = str_data[0]
    message = ' '.join(str_data[1:])

    if receiver[:1] != '@' and receiver[:1] != '+':
        return HttpResponse()
    if receiver[:1] == '+':
        is_phone = True
    else:
        is_phone = False
    if is_phone is False:
        receiver = receiver[1:]

    if chat_service.user_exists(receiver) is None:
        return HttpResponse()

    if is_phone is True:
        twilio_service.send_sms(receiver, message)

    if chat_service.user_exists(receiver) is None:
        return HttpResponse()

    is_tagged = detection_service.is_harrassment(message)
    chat_service.insert_message(sender, receiver, message)

    if is_tagged == 1:
        chat_service.set_user_tagged(sender)

    return HttpResponse()
