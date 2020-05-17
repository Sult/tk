import requests
import xmltodict

BASE_URL = 'https://gegevensmagazijn.tweedekamer.nl/SyncFeed/2.0/'
XSDS_URL = 'https://gegevensmagazijn.tweedekamer.nl/Contract/tkdata-v1-0.xsd'

response = requests.get(XSDS_URL)

data = xmltodict.parse(response.content.decode())

# get feed
response = requests.get(BASE_URL + 'Feed')
# sshuttle --dns -r sult@80.100.179.81 147.181.96.41/32