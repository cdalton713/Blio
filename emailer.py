from pathlib import Path
import os
import requests
from typing import List
from furl import furl
import webbrowser
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv, set_key
import json
from time import time
# from msg_parser import MsOxMessage
import logging
import re
from datetime import datetime
from extract_msg import Message as Msg
import tempfile

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

folder = Path(r"C:\Users\cdalt\Downloads\test")
files = folder.glob(r'*.msg')

TESTING = True
if TESTING:
    MATTER_ID = 1309009351
else:
    MATTER_ID = 1227514321
USER_ID = 345153777

BASE_DIR = Path(__file__).parent


class Api:
    def __init__(self):
        self.client_id = os.environ.get('CLIENT_ID')
        if self.client_id is None:
            self.client_id = input('ENTER CLIENT ID FROM CLIO: \t')
            set_key('.env', 'CLIENT_ID', self.client_id)

        self.client_secret = os.environ.get('CLIENT_SECRET')
        if self.client_secret is None:
            self.client_secret = input('ENTER CLIENT SECRET FROM CLIO: \t')
            set_key('.env', 'CLIENT_SECRET', self.client_secret)

        self.redirect_url = furl('https://app.clio.com/oauth/approval')
        self.auth_url = furl('https://app.clio.com/oauth/authorize')
        self.token_url = furl('https://app.clio.com/oauth/token')
        self.base_url = furl('https://app.clio.com')
        self.token = None if os.environ.get('OAUTH_TOKEN') is None else json.loads(os.environ.get('OAUTH_TOKEN'))

        self.refresh_extras = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        self.clio = OAuth2Session(client_id=self.client_id,
                                  redirect_uri=self.redirect_url.url,
                                  token=self.token,
                                  )

        self.code = os.environ.get('CLIENT_CODE')

    def _set_token(self, token):
        set_key('.env', 'OAUTH_TOKEN', json.dumps(token))
        self.clio.token = token

    def login(self):

        if self.token is not None:
            self.refresh_token()
        else:
            authorization_url, state = self.clio.authorization_url(self.auth_url.url)
            webbrowser.open(authorization_url)
            self.code = input('Enter code provided by Clio:\t')
            set_key('.env', 'CLIENT_CODE', self.code)
            set_key('.env', 'OAUTH_STATE', state)

    def authorize(self):
        token = self.clio.fetch_token(self.token_url.url, client_secret=self.client_secret,
                                      authorization_response=self.redirect_url.url,
                                      code=self.code, )
        self._set_token(token)

    def refresh_token(self):
        token = self.token
        token['expires_at'] = time() - 10

        token = self.clio.refresh_token(self.token_url.url, **self.refresh_extras)
        self._set_token(token)

    def get_who_am_i(self, fields: List[str] = None):
        if fields is None:
            fields = ['id', 'first_name', 'last_name', 'email']
        url = self.base_url.copy().add(path='/api/v4/users/who_am_i.json')
        params = {'fields': ','.join(fields)}
        response = self.clio.get(url.url, params=params)
        if response.ok:
            return response.json()['data']

    def get_contact(self, contact, fields: List[str] = None):
        if fields is None:
            fields = ['id', 'first_name', 'last_name', 'primary_email_address']
        url = self.base_url.copy().add(path='/api/v4/contacts.json')
        params = {'fields': ','.join(fields),
                  'query': contact.email}
        response = self.clio.get(url.url, params=params)
        if response.ok:
            data = {
                'email': contact.email,
                'clio': response.json()['data'],
                'outlook': contact,
                'existing': True
            }
            return data
        elif response.status_code == 404:
            data = {
                'email': contact.email,
                'clio': None,
                'outlook': contact,
                'existing': False
            }
            logger.warning(f'Contact with email {contact.email} not found')
            return data
        else:
            logger.error('ERROR')

    def get_matters(self, status: str, fields: List[str] = None):
        if fields is None:
            fields = ['id', 'display_number', 'description']
        url = self.base_url.copy().add(path='/api/v4/matters.json')
        params = {'fields': ','.join(fields),
                  'status': status}
        response = self.clio.get(url.url, params=params)
        if response.ok:
            return response.json()['data']
        else:
            logger.error('ERROR')

    def get_activity_descriptions(self, fields: List[str] = None):
        if fields is None:
            fields = ['id, name']

        url = self.base_url.copy().add(path='/api/v4/activity_descriptions.json')
        params = {'fields': ','.join(fields)}
        response = self.clio.get(url.url, params=params)
        if response.ok:
            return response.json()['data']
        else:
            logger.error('ERROR')

    def get_folder(self, matter_id: int, fields: List[str] = None):
        if fields is None:
            fields = ['id', 'etag', 'name', 'created_at', 'updated_at']
        url = self.base_url.copy().add(path='/api/v4/folders.json')
        params = {'fields': ','.join(fields),
                  'matter_id': matter_id,
                  'query': 'Attachments'}

        response = self.clio.get(url.url, params=params)
        if response.ok:
            data = response.json()
            if len(data['data']) == 0:
                self.post_folder(matter_id=matter_id)
            else:
                return data['data'][0]['id']
        elif response.status_code == 404:
            self.post_folder(matter_id=matter_id)
        else:
            logger.error('error')
            return None

        response = self.clio.get(url.url, params=params)
        if response.ok:
            data = response.json()
            if len(data['data']) == 0:
                logger.error('error')
                return None
            else:
                return data['data'][0]['id']

    def post_contact(self, contact, fields: List[str] = None):
        if fields is None:
            fields = ['id', 'first_name', 'last_name', 'primary_email_address']
        try:
            first_name, last_name = contact.name.split(' ')
        except Exception as e:
            print(e)
            first_name = ''
            last_name = contact.name
            pass

        url = self.base_url.copy().add(path='/api/v4/contacts.json')
        payload = {
            'data': {
                'first_name': first_name,
                'last_name': last_name,
                'email_addresses': [
                    {'name': 'Primary',
                     'address': contact.email,
                     'default_email': True}
                ]

            }
        }
        params = {'fields': ','.join(fields)}
        response = self.clio.post(url.url, params=params, payload=payload)
        if response.ok:
            data = {contact.email: {
                'clio': response.json()['data'],
                'outlook': contact,
                'existing': True
            }}
            return data

    def post_email(self, payload: str, fields: List[str] = None):
        if fields is None:
            fields = ['id']
        url = self.base_url.copy().add(path='/api/v4/communications.json')
        params = {'fields': ','.join(fields)}
        # payload = json.dumps(payload)
        response = self.clio.post(url.url, params=params, json=payload)
        if response.ok:
            return response.json()['data']
        else:
            logger.error('ERROR')

    def post_folder(self, matter_id: int, fields: List[str] = None, folder_name: str = 'Attachments'):
        if fields is None:
            fields = ['id', 'etag', 'name', 'created_at', 'updated_at']
        url = self.base_url.copy().add(path='/api/v4/folders.json')
        params = {'fields': ','.join(fields)}

        payload = {'data': {
            'name': folder_name,
            'parent': {
                'id': matter_id,
                'type': 'Matter'
            }
        }}

        response = self.clio.post(url.url, params=params, json=payload)
        if response.ok:
            pass
        else:
            logger.error('error')

    def post_email_attachments(self, attachment, folder_id: int, fields: List[str] = None):

        if fields is None:
            fields = ['id', 'latest_document_version{fully_uploaded}']
        params = {'fields': ','.join(fields)}

        put_url = attachment.preLoadData['data']['latest_document_version']['put_url']
        f = {'upload_file': open(attachment.longFilename, 'rb')}

        headers = {
            'x-amz-server-side-encryption': attachment.preLoadData['data']['latest_document_version']['put_headers'][0][
                'value'],
            'Content-Type': attachment.preLoadData['data']['latest_document_version']['put_headers'][1]['value']}

        response = requests.put(put_url, headers=headers, files=f)

        if response.ok:
            payload = {
                'data': {
                    'uuid': attachment.preLoadData['data']['latest_document_version']['uuid'],
                    'fully_uploaded': 'true',
                    'parent': {
                        'id': folder_id,
                        'type': 'Folder'
                    }
                }
            }
            url = self.base_url.copy().add(path=f"/api/v4/documents/{attachment.preLoadData['data']['id']}")
            attachment.payload['data'] = {**attachment.payload['data'], **payload['data']}
            response = self.clio.patch(url.url, params=params, json=attachment.payload)
            if response.ok:
                pass
            else:
                logger.error("ERROR")
        else:
            logger.error('ERROR')

    def post_attachment_time(self, msg, attachment, activity_description_id: int, price: float,
                             seconds: int, communication_id: int = None,
                             fields: List[str] = None):
        if communication_id is None:
            communication_id = msg.postedEmail['id']

        if fields is None:
            fields = ['id', 'communication{id}', 'price', 'quantity', 'date']
        params = {'fields': ','.join(fields)}
        url = self.base_url.copy().add(path='/api/v4/activities.json')

        payload = {'data': {
            'communication': {
                'id': communication_id
            },
            'user': msg.user_id,
            'type': 'TimeEntry',
            'note': attachment.longFilename,
            'date': msg.sent_datetime,
            'price': price,
            'quantity': seconds,
            'activity_description': {
                'id': activity_description_id
            }
        }
        }

        response = self.clio.post(url.url, params=params, json=payload)
        if response.ok:
            pass
        else:
            logger.error('error')

    def get_document_put_url(self, attachment, matter_id: int, fields: List[str] = None):
        if fields is None:
            fields = ['id', 'latest_document_version{uuid,put_url,put_headers}']
        params = {'fields': ','.join(fields)}
        url = self.base_url.copy().add(path='/api/v4/documents.json')

        payload = {
            "data": {
                'name': attachment.longFilename,
                'parent': {
                    'id': matter_id,
                    'type': 'Matter'
                }
            }
        }

        response = self.clio.post(url.url, params=params, json=payload)
        if response.ok:
            return response.json()
        else:
            logger.error('ERROR')


class Message(Msg):
    def __init__(self, msg_file_path):
        super().__init__(msg_file_path)
        self.file = Path(msg_file_path)

        self.contacts = {
            'from': [],
            'to': []
        }
        self.sent_datetime = datetime.strptime(self.date, '%a, %d %b %Y %H:%M:%S %z').isoformat()
        self.emailRegex = re.compile(r'(?<=\<)(.*?)(?=\>)')
        self.nameRegex = re.compile(r'^.*(?=\<)')
        self.emailPayload = None
        self.postedEmail = None

        self.matter_id = None
        self.user_id = None

    def extract_email(self, email: str):
        nameSearch = self.nameRegex.search(email)
        if nameSearch:
            name = nameSearch.group(0)
        else:
            logger.error('Name Regex did not find name in email string.')
            name = ''

        emailSearch = self.emailRegex.search(email)
        if emailSearch:
            email = emailSearch.group(0)
        else:
            logger.error('Email Regex did not find email.')
            email = ''

        return name, email

    def create_email_payload(self):
        json_msg = {
            'data': {
                'body': self.body,
                'date': self.sent_datetime,
                'matter': {
                    'id': self.matter_id
                },
                'received_at': self.sent_datetime,
                'receivers': [
                    {
                        'id': self.user_id,
                        'type': 'User'
                    }
                ],
                'senders': [
                ],
                'subject': self.subject,
                'type': 'EmailCommunication'

            }
        }

        for contact in self.contacts['from']:
            json_msg['data']['receivers'].append(
                {
                    'id': contact['clio'][0]['id'],
                    'type': 'Contact'
                }
            )

        for contact in self.contacts['to']:
            if contact['email'] != 'rick@rickdaltonlaw.com':
                json_msg['data']['senders'].append(
                    {
                        'id': contact['clio'][0]['id'],
                        'type': 'Contact'
                    }
                )
        self.emailPayload = json_msg

    def create_attachment_payload(self, attachment, document_category_id: int = 7789340):
        # Document Category ID 7789340 = Email Attachments
        # User ID 345153777 = Rick Dalton
        json_msg = {
            'data': {
                'communication_id': self.postedEmail['id'],
                'content_type': 'string',
                'document_category': {
                    'id': document_category_id
                },
                'filename': attachment.longFilename,
                'name': attachment.longFilename,
            }
        }
        attachment.payload = json_msg
        attachment.preLoadData = clio.get_document_put_url(attachment, matter_id=self.matter_id)


class TempContact:
    def __init__(self, name, email):
        self.email = email
        self.name = name


def process_messages(items: List[str], matter_id: int, user_id: int):
    msgs = []
    [msgs.append(Message(msg)) for msg in items]

    for msg in msgs:
        # msg.save_attachments()

        msg.matter_id = matter_id
        msg.user_id = user_id

        if isinstance(msg.sender, list):
            for c in msg.sender:
                name, email = msg.extract_email(c)
                contact = TempContact(name, email)
                msg.contacts['from'].append(clio.get_contact(contact))
        elif isinstance(msg.sender, str):
            name, email = msg.extract_email(msg.sender)
            contact = TempContact(name, email)
            msg.contacts['from'].append(clio.get_contact(contact))

        if msg.recipients is not None:
            [msg.contacts['to'].append(clio.get_contact(contact)) for contact in msg.recipients]

        msg.create_email_payload()

        pass
    return msgs


def upload_messages(msgs: List, attach_activity: bool = False, activity_description_id: int = None, price: float = None,
                    seconds: int = None):
    for msg in msgs:
        for contact in msg.contacts['from']:
            if not contact['existing']:
                clio.post_contact(contact)

        for contact in msg.contacts['to']:
            if not contact['existing']:
                clio.post_contact(contact)

        msg.postedEmail = clio.post_email(msg.emailPayload)

        folder_id = clio.get_folder(msg.matter_id)
        for attachment in msg.attachments:
            msg.create_attachment_payload(attachment)
            clio.post_email_attachments(attachment, folder_id=folder_id)
            if attach_activity:
                if activity_description_id is None or seconds is None or price is None:
                    logger.error('Activity ID, Seconds, and Price are needed to continue.')
                    return None

                clio.post_attachment_time(msg, attachment, activity_description_id=activity_description_id, price=price,
                                          seconds=seconds)

    pass


if __name__ == '__main__':
    clio = Api()
    clio.login()
    me = clio.get_who_am_i()
    logger.info(me['first_name'])
    logger.info(me['last_name'])
    logger.info(me['email'])

    messages = process_messages([
        r"C:\Users\cdalt\Desktop\test\Clifford B_ Stelly_ et al v Thor_ Dixie & Bank of the West - Request for Extension.msg"],
        matter_id=MATTER_ID, user_id=USER_ID)

    messages = upload_messages(messages, attach_activity=True, activity_description_id=11161981, price=100, seconds=600)
    pass
