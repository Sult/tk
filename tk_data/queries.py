# Run shell: python manage.py shell_plus

from django.db.models import Q
from django.db.models import TextField
from django.db.models import CharField
from django.db.models import FilteredRelation
from django.db.models.functions import Length

CharField.register_lookup(Length)
TextField.register_lookup(Length)


# All votes
votes = Stemming.objects


# Combined query:
votes = Stemming.objects \
    .filter(besluit__zaak__soort = 'Wetgeving') \
    .exclude(besluit__stemming_soort='') \
    .exclude(Q(besluit__zaak__titel__icontains = 'gemeente') \
        and Q(besluit__zaak__titel__icontains = 'amenvoeg')) \
    .exclude(Q(besluit__zaak__titel__icontains = 'gemeente') \
        and Q(besluit__zaak__titel__icontains = 'herindeling')) \
    .exclude(besluit__zaak__titel__icontains = 'PbEU') \
    .exclude(besluit__zaak__titel__icontains = 'PbEG') \
    .exclude(besluit__zaak__titel__icontains = 'Trb.') \
    .exclude(besluit__zaak__titel__icontains = 'tot stand gekomen Verdrag inzake') \
    .exclude(besluit__zaak__titel__icontains = 'tot stand gekomen Statuut van') \
    .exclude(besluit__zaak__titel__icontains = 'tot stand gekomen Protocol') \
    .exclude(besluit__zaak__titel__icontains = 'Implementatie van de Richtlijn') \
    .exclude(besluit__zaak__titel__icontains = 'en enige andere wetten') \
    .exclude(besluit__zaak__titel__icontains = 'Reglement voor de Gouverneur van Curaçao') \
    .filter( \
        Q(besluit__zaak__titel__contains = 'alcohol') |
        Q(besluit__zaak__titel__contains = 'asiel') |
        Q(besluit__zaak__titel__contains = 'bijstand') |
        Q(besluit__zaak__titel__contains = 'coffeeshop') |
        Q(besluit__zaak__titel__contains = 'covid') |
        Q(besluit__zaak__titel__contains = 'crisis') |
        Q(besluit__zaak__titel__contains = 'energietransitie') |
        Q(besluit__zaak__titel__contains = 'geloof') |
        Q(besluit__zaak__titel__contains = 'hulp bij') |
        Q(besluit__zaak__titel__contains = 'huur') |
        Q(besluit__zaak__titel__contains = 'kansspelen') |
        Q(besluit__zaak__titel__contains = 'kind') |
        Q(besluit__zaak__titel__contains = 'kinderopvang') |
        Q(besluit__zaak__titel__contains = 'klimaat') |
        Q(besluit__zaak__titel__contains = 'leegstand') |
        Q(besluit__zaak__titel__contains = 'loon') |
        Q(besluit__zaak__titel__contains = 'milieu') |
        Q(besluit__zaak__titel__contains = 'nationaliteit') |
        Q(besluit__zaak__titel__contains = 'onderwijs') |
        Q(besluit__zaak__titel__contains = 'opium') |
        Q(besluit__zaak__titel__contains = 'opsporing') |
        Q(besluit__zaak__titel__contains = 'ouderen') |
        Q(besluit__zaak__titel__contains = 'ouders') |
        Q(besluit__zaak__titel__contains = 'participatie') |
        Q(besluit__zaak__titel__contains = 'pensioen') |
        Q(besluit__zaak__titel__contains = 'referendum') |
        Q(besluit__zaak__titel__contains = 'reisdocument') |
        Q(besluit__zaak__titel__contains = 'religie') |
        Q(besluit__zaak__titel__contains = 'roken') |
        Q(besluit__zaak__titel__contains = 'scholen') |
        Q(besluit__zaak__titel__contains = 'school') |
        Q(besluit__zaak__titel__contains = 'socialezekerheidswetten') |
        Q(besluit__zaak__titel__contains = 'stikstof') |
        Q(besluit__zaak__titel__contains = 'tabak') |
        Q(besluit__zaak__titel__contains = 'terrorisme') |
        Q(besluit__zaak__titel__contains = 'toezicht') |
        Q(besluit__zaak__titel__contains = 'toezicht') |
        Q(besluit__zaak__titel__contains = 'uitkering') |
        Q(besluit__zaak__titel__contains = 'veehouderij') |
        Q(besluit__zaak__titel__contains = 'veiligheid') |
        Q(besluit__zaak__titel__contains = 'verbod') |
        Q(besluit__zaak__titel__contains = 'verkeer') |
        Q(besluit__zaak__titel__contains = 'vervolging') |
        Q(besluit__zaak__titel__contains = 'vreemdelingen') |
        Q(besluit__zaak__titel__contains = 'vuurwerk') |
        Q(besluit__zaak__titel__contains = 'ziek') |
        Q(besluit__zaak__titel__contains = 'zorg')) \
        .filter(besluit__zaak__soort = 'Wetgeving', besluit__zaak__titel__length__lt = 144)


# Result
bills = set()
for vote in votes:
    bills.add(vote.besluit.zaak.titel)
for title in bills:
    print('- ', title)
len(bills)


# NOTES
# - if all parties agree the ballot is not that relevant
# - if only a few vote contrarian, the ballot is (very) relevant
