import copy
import logging
import time
import uuid
from datetime import datetime

import requests
import xmltodict
from dateutil.parser import parse as parse_date

from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from requests.exceptions import SSLError

from sync_db.exceptions import EntryParseError
from sync_db.mixins import TweedeKamerMixin

logger = logging.getLogger(__name__)


class Feed(models.Model):
    url = models.URLField()
    next = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()

    @classmethod
    def sync(cls):
        """ Run feed to sync data """
        last = Feed.objects.exclude(next=None).order_by('-created_at').first()
        url = last.next if last else 'https://gegevensmagazijn.tweedekamer.nl/SyncFeed/2.0/Feed'

        while url:
            now = datetime.now()
            print("%s Saving: %s" % ('%s:%s:%s' % (now.hour, now.minute, now.second), url))
            with transaction.atomic():
                url = cls._run_sync(url)

    @classmethod
    def _run_sync(cls, url):
        response = requests.get(url)

        # force to dict
        data = xmltodict.parse(response.content.decode())

        feed = data['feed']
        entries = feed['entry']
        del feed['entry']

        next_url = [u['@href'] for u in feed['link'] if u['@rel'] == 'next']
        if next_url:
            next_url = next_url[0]

        # save feed
        feed = Feed.objects.create(
            url=url,
            next=next_url if next_url else None,
            data=feed
        )

        # add entries
        print("adding entries")
        for entry in entries:
            db_entry, _created = Entry.objects.get_or_create(id=entry['title'])
            db_entry.url = entry['id']
            db_entry.data = entry
            db_entry.save()

            # save to object
            db_entry.create_object()

        return feed.next


class Entry(models.Model):
    DATA_URL = 'https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/%s/%s'

    id = models.CharField(max_length=255, primary_key=True)
    data = models.JSONField(default=dict)

    url = models.URLField(max_length=255, blank=True, null=True)
    next = models.URLField(max_length=255, blank=True, null=True)

    def create_object(self):
        model = self.get_model(self.data['category'])
        parsed_data = self.parse_entry_data(model)
        try:
            obj = model.objects.get(id=parsed_data['id'])
            for key, value in parsed_data.items():
                setattr(obj, key, value)
            obj.save()
            return obj
        except model.DoesNotExist:
            return model.objects.create(**parsed_data)

    @staticmethod
    def get_key_name(field_name):
        parts = field_name.split('_')
        return '%s%s' % (parts[0], ''.join(p.title() for p in parts[1:]))

    def rename_namespace(self, data):
        for key in copy.deepcopy(data).keys():
            # drop namespaces
            if key.startswith('ns1:'):
                data[key.replace('ns1:', '')] = data[key]
            elif key.startswith('@ns1:'):
                data[key.replace('@ns1:', '')] = data[key]
        return data

    def get_related_obj(self, field, content):
        """ get related object from db, or pull from api otherwise """

        name_mapping = {
            "voortouwcommissie": "commissie",
            "huidigeDocumentVersie": "documentversie",
        }
        # no idea why this happens but seems it can
        ignore_mapping = {
            "fractie": [ActiviteitActor, ]
        }

        key = self.get_key_name(field.name)
        try:
            if content[key].get('@xsi:nil') == 'true':
                return
            return field.related_model.objects.get(id=content[key]['@ref'])
        except field.related_model.DoesNotExist:
            try:
                response = requests.get(self.DATA_URL % (name_mapping.get(key, key), content[key]['@ref']))
                obj = field.related_model.create_from_json(response.json())
                return obj
            except SSLError:
                print("SSL error: retrying in a bit")
                time.sleep(10)
                return self.get_related_obj(field, content)

            except Exception as exc:
                breakpoint()
                raise
        except KeyError as exc:
            if exc.args[0] in ignore_mapping and self.get_model(self.data['category']) in ignore_mapping[exc.args[0]]:
                return
        except Exception as exc:
            breakpoint()
            raise

    def parse_entry_data(self, model):
        # always should be an id
        content = copy.deepcopy(self.rename_namespace(self.data['content'])[self.data['category']['@term']])
        parsed = {'id': uuid.UUID(content.get('@id'))}

        content = self.rename_namespace(content)
        parsed['verwijderd'] = content.get('@tk:verwijderd') == 'true'
        if parsed['verwijderd']:
            return parsed

        if content.get('@tk:bijgewerkt'):
            breakpoint()
            parsed['gewijzigd_op'] = parse_date(content.get('@tk:bijgewerkt'))

        fields = model._meta.get_fields()
        for field in fields:
            if isinstance(field, models.ForeignKey):
                obj = self.get_related_obj(field, content)
                if obj:
                    parsed[field.name] = obj

            elif field.name in content:
                if content[field.name] == {'@xsi:nil': 'true'}:
                    parsed[field.name] = None
                else:
                    if isinstance(field, models.DateTimeField):
                        parsed[field.name] = parse_date(content[field.name])
                    elif isinstance(field, models.BooleanField):
                        parsed[field.name] = content[field.name] == 'true'
                    elif isinstance(field, models.NullBooleanField):
                        breakpoint()
                    else:
                        parsed[field.name] = content[field.name]

        return parsed

    @staticmethod
    def get_model(category):
        try:
            return apps.get_model('sync_db', category['@term'][0].upper() + category['@term'][1:])
        except Exception:
            raise EntryParseError("No category found for %s" % category)


class Commissie(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Commissie """

    nummer = models.CharField(max_length=255, blank=True, null=True)
    soort = models.CharField(max_length=255, blank=True, null=True)
    afkorting = models.CharField(max_length=255, blank=True, null=True)
    naam_nl = models.CharField(max_length=255, blank=True, null=True)
    naam_en = models.CharField(max_length=255, blank=True, null=True)
    naam_web_nl = models.CharField(max_length=255, blank=True, null=True)
    naam_web_en = models.CharField(max_length=255, blank=True, null=True)
    inhoudsopgave = models.CharField(max_length=255, blank=True, null=True)
    datum_actief = models.DateTimeField(blank=True, null=True)
    datum_inactief = models.DateTimeField(blank=True, null=True)


class Activiteit(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Activiteit """

    voortouwcommissie = models.ForeignKey('sync_db.Commissie', null=True, blank=True, on_delete=models.SET_NULL)

    soort = models.CharField(max_length=255, blank=True, null=True)
    nummer = models.CharField(max_length=255, blank=True, null=True)
    onderwerp = models.TextField(null=True, blank=True)
    datum_soort = models.TextField(null=True, blank=True)
    datum = models.DateTimeField(blank=True, null=True)
    aanvangstijd = models.DateTimeField(blank=True, null=True)
    eindtijd = models.DateTimeField(blank=True, null=True)
    locatie = models.TextField(null=True, blank=True)
    besloten = models.BooleanField(null=True, default=None)
    status = models.CharField(max_length=255, blank=True, null=True)
    vergaderjaar = models.CharField(max_length=255, blank=True, null=True)
    kamer = models.TextField(null=True, blank=True)
    noot = models.TextField(null=True, blank=True)
    vrs_nummer = models.CharField(max_length=255, blank=True, null=True)
    sid_voortouw = models.CharField(max_length=255, blank=True, null=True)
    voortouw_naam = models.CharField(max_length=255, blank=True, null=True)
    voortouw_korte_naam = models.CharField(max_length=255, blank=True, null=True)


class ActiviteitActor(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/ActiviteitActor """

    activiteit = models.ForeignKey('sync_db.Activiteit', null=True, blank=True, on_delete=models.SET_NULL)
    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)
    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)
    commissie = models.ForeignKey('sync_db.Commissie', null=True, blank=True, on_delete=models.SET_NULL)

    actor_naam = models.CharField(max_length=255, blank=True, null=True)
    actor_fractie = models.CharField(max_length=255, blank=True, null=True)
    relatie = models.CharField(max_length=255, blank=True, null=True)
    volgorde = models.IntegerField(blank=True, null=True)
    functie = models.CharField(max_length=255, blank=True, null=True)
    spreektijd = models.CharField(max_length=255, blank=True, null=True)


class AgendaPunt(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Agendapunt """

    nummer = models.CharField(max_length=255, blank=True, null=True)
    onderwerp = models.TextField(null=True, blank=True)
    aanvangstijd = models.DateTimeField(null=True, blank=True)
    eindtijd = models.DateTimeField(null=True, blank=True)
    volgorde = models.IntegerField(blank=True, null=True)
    rubriek = models.CharField(max_length=255, blank=True, null=True)
    noot = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=255, blank=True, null=True)


class Besluit(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Besluit """

    agendapunt = models.ForeignKey('sync_db.Agendapunt', null=True, blank=True, on_delete=models.SET_NULL)
    zaak = models.ForeignKey('sync_db.Zaak', null=True, blank=True, on_delete=models.SET_NULL)

    stemming_soort = models.CharField(max_length=255, blank=True, null=True)
    besluit_soort = models.CharField(max_length=255, blank=True, null=True)
    besluit_tekst = models.TextField(null=True, blank=True)
    opmerking = models.TextField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    agendapunt_zaak_besluit_volgorde = models.IntegerField(blank=True, null=True)


class CommissieContactinformatie(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/CommissieContactinformatie """

    commissie = models.ForeignKey('sync_db.Commissie', null=True, blank=True, on_delete=models.SET_NULL)

    soort = models.CharField(max_length=255, blank=True, null=True)
    waarde = models.TextField(null=True, blank=True)


class CommissieZetel(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/CommissieZetel """

    commissie = models.ForeignKey('sync_db.Commissie', null=True, blank=True, on_delete=models.SET_NULL)

    gewicht = models.IntegerField(null=True, blank=True)


class CommissieZetelVastPersoon(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/CommissieZetelVastPersoon """

    commissie_zetel = models.ForeignKey('sync_db.CommissieZetel', null=True, blank=True, on_delete=models.SET_NULL)
    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    functie = models.CharField(max_length=255, blank=True, null=True)
    van = models.DateTimeField(blank=True, null=True)
    tot_en_met = models.DateTimeField(blank=True, null=True)


class CommissieZetelVastVacature(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/CommissieZetelVastVacature """

    commissie_zetel = models.ForeignKey('sync_db.CommissieZetel', null=True, blank=True, on_delete=models.SET_NULL)
    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)

    functie = models.CharField(max_length=255, blank=True, null=True)
    van = models.DateTimeField(blank=True, null=True)
    tot_en_met = models.DateTimeField(blank=True, null=True)


class CommissieZetelVervangerPersoon(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/CommissieZetelVastVacature """

    commissie_zetel = models.ForeignKey('sync_db.CommissieZetel', null=True, blank=True, on_delete=models.SET_NULL)
    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    functie = models.CharField(max_length=255, blank=True, null=True)
    van = models.DateTimeField(blank=True, null=True)
    tot_en_met = models.DateTimeField(blank=True, null=True)


class CommissieZetelVervangerVacature(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/CommissieZetelVervangerVacature """

    commissie_zetel = models.ForeignKey('sync_db.CommissieZetel', null=True, blank=True, on_delete=models.SET_NULL)
    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)

    functie = models.CharField(max_length=255, blank=True, null=True)
    van = models.DateTimeField(blank=True, null=True)
    tot_en_met = models.DateTimeField(blank=True, null=True)


class Document(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Document """

    huidige_document_versie = models.ForeignKey('sync_db.DocumentVersie', related_name='huidige_document_versie',
                                                null=True, blank=True, on_delete=models.SET_NULL)

    soort = models.CharField(max_length=255, blank=True, null=True)
    document_nummer = models.CharField(max_length=255, blank=True, null=True)
    titel = models.TextField(blank=True, null=True)
    onderwerp = models.TextField(blank=True, null=True)
    datum = models.DateTimeField(null=True, blank=True)
    vergaderjaar = models.CharField(max_length=255, blank=True, null=True)
    kamer = models.IntegerField(null=True, blank=True)
    volgnummer = models.IntegerField(null=True, blank=True)
    citeertitel = models.TextField(null=True, blank=True)
    alias = models.CharField(max_length=255, blank=True, null=True)
    document_registratie = models.DateTimeField(null=True, blank=True)
    datum_ontvangst = models.DateTimeField(null=True, blank=True)
    aanhangselnummer = models.CharField(max_length=255, blank=True, null=True)
    kenmerk_afzender = models.CharField(max_length=255, blank=True, null=True)
    organisatie = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    content_length = models.IntegerField(null=True, blank=True)


class DocumentActor(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/DocumentActor """

    document = models.ForeignKey('sync_db.Document', null=True, blank=True, on_delete=models.SET_NULL)
    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)
    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)
    commissie = models.ForeignKey('sync_db.Commissie', null=True, blank=True, on_delete=models.SET_NULL)

    actor_naam = models.CharField(max_length=255, blank=True, null=True)
    actor_fractie = models.CharField(max_length=255, blank=True, null=True)
    functie = models.CharField(max_length=255, blank=True, null=True)
    relatie = models.CharField(max_length=255, blank=True, null=True)
    sid_actor = models.CharField(max_length=255, blank=True, null=True)


class DocumentVersie(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/DocumentActor """

    document = models.ForeignKey('sync_db.Document', null=True, blank=True, on_delete=models.SET_NULL)

    status = models.CharField(max_length=255, blank=True, null=True)
    versienummer = models.IntegerField(null=True, blank=True)
    bestandsgrootte = models.IntegerField(null=True, blank=True)
    extensie = models.CharField(max_length=255, blank=True, null=True)
    datum = models.DateTimeField(null=True, blank=True)


class Fractie(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Fractie """

    nummer = models.CharField(max_length=255, blank=True, null=True)
    afkorting = models.CharField(max_length=255, blank=True, null=True)
    naam_nl = models.CharField(max_length=255, blank=True, null=True)
    naam_en = models.CharField(max_length=255, blank=True, null=True)
    aantal_zetels = models.IntegerField(null=True, blank=True)
    aantal_stemmen = models.IntegerField(null=True, blank=True)
    datum_actief = models.DateTimeField(blank=True, null=True)
    datum_inactief = models.DateTimeField(blank=True, null=True)

    content_type = models.CharField(max_length=255, blank=True, null=True)
    content_length = models.IntegerField(null=True, blank=True)


class FractieAanvullendeGegeven(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/FractieAanvullendGegeven """

    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)

    soort = models.CharField(max_length=255, blank=True, null=True)
    waarde = models.TextField(null=True, blank=True)


class FractieZetel(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/FractieZetel """

    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)

    gewicht = models.IntegerField(null=True, blank=True)


class FractieZetelPersoon(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/FractieZetelPersoon """

    fractie_zetel = models.ForeignKey('sync_db.FractieZetel', null=True, blank=True, on_delete=models.SET_NULL)
    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    van = models.DateTimeField(blank=True, null=True)
    tot_en_met = models.DateTimeField(blank=True, null=True)


class FractieZetelVacature(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/FractieZetelVacature """

    fractie_zetel = models.ForeignKey('sync_db.FractieZetel', null=True, blank=True, on_delete=models.SET_NULL)

    functie = models.CharField(max_length=255, blank=True, null=True)
    van = models.DateTimeField(blank=True, null=True)
    tot_en_met = models.DateTimeField(blank=True, null=True)


class Kamerstukdossier(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Kamerstukdossier """

    titel = models.TextField(null=True, blank=True)
    citeertitel = models.TextField(null=True, blank=True)
    allias = models.TextField(null=True, blank=True)
    nummer = models.IntegerField(null=True, blank=True)
    toevoeging = models.CharField(max_length=255, blank=True, null=True)
    hoogste_volgnummer = models.IntegerField(null=True, blank=True)
    afgesloten = models.BooleanField(null=True, default=None)
    kamer = models.CharField(max_length=255, blank=True, null=True)


class Persoon(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Persoon """

    nummer = models.IntegerField(null=True, blank=True)
    titels = models.TextField(null=True, blank=True)
    initialen = models.CharField(max_length=255, blank=True, null=True)
    tussenvoegsel = models.CharField(max_length=255, blank=True, null=True)
    achternaam = models.CharField(max_length=255, blank=True, null=True)
    voornamen = models.CharField(max_length=255, blank=True, null=True)
    roepnaam = models.CharField(max_length=255, blank=True, null=True)
    geslacht = models.CharField(max_length=255, blank=True, null=True)
    functie = models.CharField(max_length=255, blank=True, null=True)
    geboortdedatum = models.DateTimeField(null=True, blank=True)
    geboorteplaats = models.CharField(max_length=255, blank=True, null=True)
    geboorteland = models.CharField(max_length=255, blank=True, null=True)
    overlijdens_plaats = models.CharField(max_length=255, blank=True, null=True)
    woonplaats = models.CharField(max_length=255, blank=True, null=True)
    land = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    content_length = models.IntegerField(null=True, blank=True)


class PersoonContactinformatie(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/PersoonContactinformatie """

    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    soort = models.CharField(max_length=255, null=True, blank=True)
    waarde = models.TextField(null=True, blank=True)


class PersoonGeschenk(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/PersoonGeschenk """

    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    omschrijving = models.TextField(null=True, blank=True)
    datum = models.DateTimeField(null=True, blank=True)


class PersoonLoopbaan(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/PersoonLoopbaan """

    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    functie = models.CharField(max_length=255, blank=True, null=True)
    werkgever = models.CharField(max_length=255, blank=True, null=True)
    omschrijving_nl = models.TextField(null=True, blank=True)
    omschrijving_en = models.TextField(null=True, blank=True)
    plaats = models.CharField(max_length=255, blank=True, null=True)
    van = models.CharField(max_length=255, blank=True, null=True)
    tot_en_met = models.CharField(max_length=255, blank=True, null=True)


class PersoonNevenfunctie(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/PersoonNevenfunctie """

    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    omschrijving = models.TextField(null=True, blank=True)
    periode_van = models.CharField(max_length=255, blank=True, null=True)
    periode_tot_en_met = models.CharField(max_length=255, blank=True, null=True)
    is_actief = models.BooleanField(null=True)
    vergoeding_soort = models.CharField(max_length=255, blank=True, null=True)
    vergoeding_toelichting = models.CharField(max_length=255, blank=True, null=True)


class PersoonNevenfunctieInkomsten(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/PersoonNevenfunctieInkomsten """

    persoon_nevenfunctie = models.ForeignKey('sync_db.PersoonNevenfunctie', null=True, blank=True, on_delete=models.SET_NULL)

    jaar = models.CharField(max_length=255, blank=True, null=True)
    bedrag_soort = models.CharField(max_length=255, blank=True, null=True)
    bedrag_voorvoegsel = models.CharField(max_length=255, blank=True, null=True)
    bedrag_valuta = models.CharField(max_length=255, blank=True, null=True)
    bedrag = models.DecimalField(max_digits=11, decimal_places=2, null=True, blank=True)
    bedrag_achtervoegsel = models.CharField(max_length=255, blank=True, null=True)
    frequentie = models.CharField(max_length=255, blank=True, null=True)
    frequentie_beschrijving = models.CharField(max_length=255, blank=True, null=True)
    opmerking = models.CharField(max_length=255, blank=True, null=True)


class PersoonOnderwijs(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/PersoonOnderwijs """

    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    opleiding_nl = models.CharField(max_length=255, blank=True, null=True)
    opleiding_en = models.TextField(null=True, blank=True)
    instelling = models.CharField(max_length=255, blank=True, null=True)
    plaats = models.CharField(max_length=255, blank=True, null=True)
    van = models.CharField(max_length=255, blank=True, null=True)
    tot_en_met = models.CharField(max_length=255, blank=True, null=True)


class PersoonReis(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/PersoonReis """

    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)

    doel = models.TextField(blank=True, null=True)
    bestemming = models.CharField(max_length=255, blank=True, null=True)
    van = models.DateTimeField(blank=True, null=True)
    tot_en_met = models.DateTimeField(blank=True, null=True)
    betaald_door = models.TextField(blank=True, null=True)


class Reservering(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Reservering """

    nummer = models.CharField(max_length=255, blank=True, null=True)
    status_code = models.CharField(max_length=255, blank=True, null=True)
    status_naam = models.CharField(max_length=255, blank=True, null=True)
    activiteit_nummer = models.CharField(max_length=255, blank=True, null=True)


class Stemming(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Stemming """

    besluit = models.ForeignKey('sync_db.Besluit', null=True, blank=True, on_delete=models.SET_NULL)
    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)
    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)

    soort = models.CharField(max_length=255, blank=True, null=True)
    fractie_grootte = models.IntegerField(null=True, blank=True)
    actor_naam = models.CharField(max_length=255, blank=True, null=True)
    actor_fractie = models.CharField(max_length=255, blank=True, null=True)
    vergissing = models.BooleanField(null=True, default=None)
    sid_actor_lid = models.CharField(max_length=255, blank=True, null=True)
    sid_actor_fractie = models.CharField(max_length=255, blank=True, null=True)


class Vergadering(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Vergadering """

    soort = models.CharField(max_length=255, blank=True, null=True)
    titel = models.TextField(null=True, blank=True)
    zaal = models.CharField(max_length=255, blank=True, null=True)
    vergaderjaar = models.CharField(max_length=255, blank=True, null=True)
    vergadering_nummer = models.IntegerField(null=True, blank=True)
    datum = models.DateTimeField(null=True, blank=True)
    aanvangstijd = models.DateTimeField(null=True, blank=True)
    sluiting = models.DateTimeField(null=True, blank=True)
    kamer = models.CharField(max_length=255, blank=True, null=True)


class Verslag(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Verslag """

    vergadering = models.ForeignKey('sync_db.Vergadering', null=True, blank=True, on_delete=models.SET_NULL)

    soort = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    content_length = models.IntegerField(null=True, blank=True)


class Zaak(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Zaak """

    nummer = models.CharField(max_length=255, blank=True, null=True)
    soort = models.CharField(max_length=255, blank=True, null=True)
    titel = models.TextField(null=True, blank=True)
    citeertitel = models.TextField(null=True, blank=True)
    alias = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    onderwerp = models.TextField(null=True, blank=True)
    gestart_op = models.CharField(max_length=255, blank=True, null=True)
    orgainsatie = models.CharField(max_length=255, blank=True, null=True)
    grodnslag_voorhang = models.CharField(max_length=255, blank=True, null=True)
    termijn = models.DateTimeField(blank=True, null=True)
    vergader_jaar = models.CharField(max_length=255, blank=True, null=True)
    volgnummer = models.IntegerField(blank=True, null=True)
    huidige_behandel_status = models.CharField(max_length=255, blank=True, null=True)
    afgedaan = models.BooleanField(null=True, default=None)
    groot_project = models.BooleanField(null=True)
    kabinet_appreciatie = models.CharField(max_length=255, blank=True, null=True)


class ZaakActor(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/ZaakActor """

    zaak = models.ForeignKey('sync_db.Zaak', null=True, blank=True, on_delete=models.SET_NULL)
    persoon = models.ForeignKey('sync_db.Persoon', null=True, blank=True, on_delete=models.SET_NULL)
    fractie = models.ForeignKey('sync_db.Fractie', null=True, blank=True, on_delete=models.SET_NULL)
    commissie = models.ForeignKey('sync_db.Commissie', null=True, blank=True, on_delete=models.SET_NULL)

    actor_naam = models.CharField(max_length=255, null=True, blank=True)
    actor_fractie = models.CharField(max_length=255, null=True, blank=True)
    actor_afkorting = models.CharField(max_length=255, null=True, blank=True)
    functie = models.CharField(max_length=255, null=True, blank=True)
    relatie = models.CharField(max_length=255, null=True, blank=True)


class Zaal(TweedeKamerMixin, models.Model):
    """ https://opendata.tweedekamer.nl/documentatie/Zaal """

    naam = models.CharField(max_length=255, null=True, blank=True)
    sys_code = models.IntegerField(null=True, blank=True)


class BuggedModel(models.Model):
    """ ugly model to keep track of what objects couldnt (fully) be saved with relations etc """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_object = GenericForeignKey('content_type', 'object_id')

    error = models.TextField(null=True, blank=True)
