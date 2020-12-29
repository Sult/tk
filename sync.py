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


from django.db.models import CharField
from django.db.models.functions import Length
TextField.register_lookup(Length)
serie = Stemming.objects.exclude(
    besluit__stemming_soort=''
).prefetch_related(
    Prefetch('zaak', queryset=Zaak.objects.filter(soort='Wetgeving', titel__length__lt=144))
)


counter = 0
length = Besluit.objects.count()
for besluit in Besluit.objects.all():
    try:
        besluit.zaak = Zaak.objects.get(id=besluit.data['content']['besluit']['zaak']['@ref'])
        besluit.save(parsed_data=False)
    except:
        pass
    counter += 1
    if counter % 1000 == 0:
        print('%s/%s' % (counter, length))


counter = 0
entries = Entry.objects.filter(saved=False)
length = entries.count()

for entry in entries:
    entry.save()
    counter += 1
    if counter % 1000 == 0:
        print('%s/%s' % (counter, length))



data = Stemming.objects.exclude