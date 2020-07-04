import requests
import xmltodict

BASE_URL = 'https://gegevensmagazijn.tweedekamer.nl/SyncFeed/2.0/'
XSDS_URL = 'https://gegevensmagazijn.tweedekamer.nl/Contract/tkdata-v1-0.xsd'

response = requests.get(XSDS_URL)

data = xmltodict.parse(response.content.decode())

# get feed
response = requests.get(BASE_URL + 'Feed')
# sshuttle --dns -r sult@codesaur.nl 147.181.96.41/32


before = BuggedModel.objects.all().count()
for bugged in BuggedModel.objects.all():
    obj = bugged.content_object.__class__.objects.get(pk=bugged.object_id)
    obj.save()
    if obj.saved_related:
        bugged.delete()

after = BuggedModel.objects.all().count()
print(before - after)


import json, requests
from django.apps import apps
with open('missing.json', 'r') as f:
    data = json.dumps(f.read())

url = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/%s/%s"

for model_str, ids in data.items():
    model = apps.get_model('sync_db', model_str)
