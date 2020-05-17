import time
import requests
import xmltodict

from sync_db.models import Feed, Entry

"""
Voor iedere <entry> die u tegenkomt: sla de Guid en de XML inhoud van deze entry, 
samen met de <link rel=”next”> waarde op in de database. Dit "<link>" element bevat de link om de volgende request te maken. 
Zo weet u precies waar u gebleven bent.

Indien de <entry> een <link rel="enclosure"> element bevat dan betekent dit dat er een achterliggend bestand beschikbaar is. 
Dit bestand kunt u downloaden door deze enclosure link te volgen.
Nadat u alle beschikbare <entry> elementen van het verzoek heeft verwerkt, 
maakt u een volgende request op basis van de <link rel=”next”> waarde van het laatst verwerkte <entry>.

Herhaal stap 1 en 2 totdat u geen <entry> resultaten meer terugkrijgt. 
Dit betekent dat u alle entiteiten heeft binnengehaald. 
Indicatie: op het moment van schrijven bevat de SyncFeed ongeveer 3,5 miljoen entiteiten.
"""


BASE_URL = 'https://gegevensmagazijn.tweedekamer.nl/SyncFeed/2.0/'


def sync(next=None):
    if not next:
        next = 'https://gegevensmagazijn.tweedekamer.nl/SyncFeed/2.0/Feed'

    while next:
        print("pulling: %s" % next)
        response = requests.get(next)

        # force to dict
        data = xmltodict.parse(response.content.decode())

        feed = data['feed']
        entries = feed['entry']
        del feed['entry']

        url = next
        next = [u['@href'] for u in feed['link'] if u['@rel'] == 'next']
        if next:
            next = next[0]

        # save feed
        Feed.objects.create(
            url=url,
            next=next if next else None,
            data=feed
        )

        for entry in entries:
            try:
                db_entry, _created = Entry.objects.get_or_create(id=entry['title'])
                db_entry.url = entry['id']
                db_entry.data = entry
                db_entry.save()
            except Exception as exc:
                breakpoint()
                raise

        # time.sleep(0.5)
