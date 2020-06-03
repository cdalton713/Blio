from requests_oauthlib import OAuth2Session
import requests
import json
import time
from furl import furl
import pandas as pd
client_id = r'38QzyOM5u6EhhXCHaFWK688uzExquOKWdHmzNSJN'
client_secret = 'KZv9Cdc594M1AlSMaN2tQhB3iRAj2VtreTgvKjSY'
redirect_url = 'https://app.clio.com/oauth/approval'
auth_url = 'https://app.clio.com/oauth/authorize'
token_url = 'https://app.clio.com/oauth/token'
base_url = 'https://app.clio.com'

user_id = 345153777

TESTING = True

payload = {}
headers = {
    'Authorization': 'Bearer vMdG0JipiIPchbCgwMQi3TBr0rzPKza9AwgINkea',
    'Content-Type': 'application/json',
    'Cookie': '_session_id=555287e1014947f68443aa8afcacb6ae; __cfduid=dcce8d786fb7dcaa865bbb502592470f21590453627; _ga=GA1.2.1484458601.1590453627; _gid=GA1.2.1923325606.1590453627; clio_first_touch={%22referrer%22:null%2C%22landing_url%22:%22https://account.clio.com/login?login_challenge=efb5606b63d04148be8685108a3ff1fe%22%2C%22ajs_user_id%22:null%2C%22ajs_anonymous_id%22:null%2C%22timestamp%22:1590453626712%2C%22gclid%22:null%2C%22utm_campaign%22:null%2C%22utm_source%22:null%2C%22utm_medium%22:null%2C%22utm_content%22:null%2C%22utm_term%22:null%2C%22sem_ad_group_id%22:null}; clio_last_touch_refresh_count=2; clio_last_touch={%22referrer%22:null%2C%22landing_url%22:%22https://account.clio.com/login?login_challenge=263ec406fec347ef90135690d993e95b%22%2C%22ajs_user_id%22:null%2C%22ajs_anonymous_id%22:null%2C%22timestamp%22:1590453636697%2C%22session_count%22:2%2C%22gclid%22:null%2C%22utm_campaign%22:null%2C%22utm_source%22:null%2C%22utm_medium%22:null%2C%22utm_content%22:null%2C%22utm_term%22:null%2C%22sem_ad_group_id%22:null}; XSRF-TOKEN=2S8s5bbCTMYqKjKJHdi%2FLJWlyfyOh%2FXATSfJnMX8qB2Plktomo2PjhQb2iFCrP%2Bir%2BzLsfKA9xGi%2BJ4PwWKXFw%3D%3D'
}


# response = requests.request("GET", url, headers=headers, data=payload)

# coms = json.loads(response.text.encode('utf8'))


# all_com = json.loads(all_communications.content.decode('utf-8'))

def get_all_data(url):
    combined_data = []
    response = requests.request("GET", url, headers=headers)

    if response.ok:
        result = response.json()
        [combined_data.append(r) for r in result['data']]
        while 'meta' in result and 'paging' in result['meta'] and 'next' in result['meta']['paging']:
            response = requests.request("GET", result['meta']['paging']['next'], headers=headers)
            if response.ok:
                result = response.json()
                [combined_data.append(r) for r in result['data']]

    return combined_data



def bulk_add_document_times(matter_id: int, fields: list = None, document_category_id: int = None,
                            extra_args=None,
                            activity_type: int = 11161981, ):
    # DOCKETBIRD JSON: https://app.clio.com/iris/folders/3060864976/list.json?limit=2000

    if extra_args is None:
        extra_args = {}
    if fields is None:
        fields = ['id', 'name', 'filename', 'document_category',  'size', 'created_at']

    url = furl(base_url)
    url /= '/api/v4/documents.json'
    url.args['matter_id'] = matter_id
    url.args['fields'] = ','.join(fields)
    url.args['document_category_id'] = document_category_id
    url.args['limit'] = '200'
    url.add(extra_args)
    data = get_all_data(url.url)
    remaining = 10
    post_data = []
    for i, d in enumerate(data):
        pl = {'data': {
            'user': {
                'id': user_id
            },
            "document_version": {
                "filename": d['filename'],
                "size": d['size']
            },
            'type': 'TimeEntry',
            'note': d['name'],
            'date': d['created_at'],
            'activity_description': {
                'id': activity_type,
            },
            'fields': 'id,communication{id},calendar_entry{id,calendar_owner_id},document_version{id},price,quantity,rounded_quantity,flat_rate,date,matter{id,display_number,billable,billing_method,description},matter_note,non_billable,contact_note{id},user{id,name,clio_connect,enabled},updated_at,contingency_fee,type,billed,on_bill,bill{id},note,posted_at,total,timer{id,start_time,elapsed_time},vendor{id,name,last_name,first_name,middle_name,type},reference,expense_category{id,name,entry_type,utbms_code},activity_description{id,name,type,rate,utbms_task_id,utbms_activity_id},utbms_expense{id,name},non_billable_total'
        }}
        if TESTING:
            post_data.append(pl)
        else:
            post_url = "https://app.clio.com/api/v4/activities.json"
            if remaining < 5:
                time.sleep(10)
            response = requests.request("POST", post_url, headers=headers, data=json.dumps(pl))
            remaining = response.headers.get('X-RateLimit-Remaining')
            print("{}, {}".format(i, response))
            # if i > 0 and i % 45 == 0:
            #     time.sleep(60)
    if TESTING:
        df = pd.concat(post_data)
        df.to_clipboard()
        pass

def bulk_update_communications(matter_id: int, fields: list, price: float, extra_args: dict, payload: dict,
                               activity_type: int = 11161981):
    if fields is None:
        fields = ['id', 'subject', 'body', 'type', 'date']

    url = furl(base_url)
    url /= '/api/v4/communications.json'
    url.args['id'] = matter_id
    url.args['fields'] = ','.join(fields)
    url.set(args=extra_args)
    response = requests.request("GET", url.url, headers=headers, data=payload)
    if response.ok:
        communications = json.loads(response.json())

        for i, communications in enumerate(communications['data']):
            pl = {'data': {
                'communication': {'id': communications['id']},
                'calendar_entry': {},
                'document_version': {},
                'price': price,
                'quantity': 360,
                'date': communications['date'],
                'matter': {
                    'id': matter_id
                },
                'non_billable': 'false',
                'contact_note': {
                    'id': 'null'
                },
                'user': {
                    'id': user_id
                },
                'type': 'TimeEntry',
                'note': communications['subject'],
                'vendor': {
                    'id': 'null'
                },
                'reference': 'null',
                'activity_description': {
                    'id': activity_type,

                    'utbms_task_id': 'null',
                    'utbms_activity_id': 'null'
                },
                'fields': 'id,communication{id},calendar_entry{id,calendar_owner_id},document_version{id},price,quantity,rounded_quantity,flat_rate,date,matter{id,display_number,billable,billing_method,description},matter_note,non_billable,contact_note{id},user{id,name,clio_connect,enabled},updated_at,contingency_fee,type,billed,on_bill,bill{id},note,posted_at,total,timer{id,start_time,elapsed_time},vendor{id,name,last_name,first_name,middle_name,type},reference,expense_category{id,name,entry_type,utbms_code},activity_description{id,name,type,rate,utbms_task_id,utbms_activity_id},utbms_expense{id,name},non_billable_total'
            }}
            # payload = "{\n    \"data\": {\n        \"communication\": {\n            \"id\": " + str(communications[
            #                                                                                              'id']) + "\n        },\n        \"calendar_entry\": {},\n        \"document_version\": {},\n        \"price\": \"1500.00\",\n         \"quantity\": 360,\n        \"date\": \"" + str(
            #     communications[
            #         'date']) + "\",\n        \"matter\": {\n            \"id\": 1227514321\n        },\n        \"non_billable\": false,\n        \"contact_note\": {\n            \"id\": \"null\"\n        },\n        \"user\": {\n            \"id\": 345153777\n        },\n        \"type\": \"TimeEntry\",\n         \"note\": \"" + str(
            #     communications[
            #         'subject']) + "\",\n        \"vendor\": {\n            \"id\": null\n        },\n        \"reference\": null,\n        \"activity_description\": {\n            \"id\": 11161981,\n            \"utbms_task_id\": null,\n       " \
            #                       "     \"utbms_activity_id\": null\n        },\n        \"utbms_expense\": {\n            \"id\": \"null\"\n        }\n    },\n    \"fields\": \"id,communication{id},calendar_entry{id,calendar_owner_id},document_version{id},price,quantity,rounded_quantity,flat_rate,date,matter{id,display_number,billable,billing_method,description},matter_note,non_billable,contact_note{id},user{id,name,clio_connect,enabled},updated_at,contingency_fee,type,billed,on_bill,bill{id},note,posted_at,total,timer{id,start_time,elapsed_time},vendor{id,name,last_name,first_name,middle_name,type},reference,expense_category{id,name,entry_type,utbms_code},activity_description{id,name,type,rate,utbms_task_id,utbms_activity_id},utbms_expense{id,name},non_billable_total\"\n}"
            #
            # # payload = "{\n    \"data\": {\n        \"communication\": {\n            \"id\": 700195321\n        },\n        \"calendar_entry\": {},\n        \"document_version\": {},\n        \"price\": \"1500.00\",\n         \"quantity\": 360,\n        \"date\": \"2020-01-30\",\n        \"matter\": {\n            \"id\": 1227514321\n        },\n        \"non_billable\": false,\n        \"contact_note\": {\n            \"id\": \"null\"\n        },\n        \"user\": {\n            \"id\": 345153777\n        },\n        \"type\": \"TimeEntry\",\n        \"note\": \"dfdf\",\n        \"vendor\": {\n            \"id\": null\n        },\n        \"reference\": null,\n        \"activity_description\": {\n            \"id\": 11161981,\n            \"utbms_task_id\": null,\n            \"utbms_activity_id\": null\n        },\n        \"utbms_expense\": {\n            \"id\": \"null\"\n        }\n    },\n    \"fields\": \"id,communication{id},calendar_entry{id,calendar_owner_id},document_version{id},price,quantity,rounded_quantity,flat_rate,date,matter{id,display_number,billable,billing_method,description},matter_note,non_billable,contact_note{id},user{id,name,clio_connect,enabled},updated_at,contingency_fee,type,billed,on_bill,bill{id},note,posted_at,total,timer{id,start_time,elapsed_time},vendor{id,name,last_name,first_name,middle_name,type},reference,expense_category{id,name,entry_type,utbms_code},activity_description{id,name,type,rate,utbms_task_id,utbms_activity_id},utbms_expense{id,name},non_billable_total\"\n}"

            post_url = "https://app.clio.com/api/v4/activities.json"

            response = requests.request("POST", post_url, headers=headers, data=pl)
            print("{}, {}".format(i, response))
            if i > 0 and i % 45 == 0:
                time.sleep(60)


if __name__ == '__main__':
    bulk_add_document_times(matter_id=1227514321, document_category_id=27714151)
