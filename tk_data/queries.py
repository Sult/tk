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
    .exclude(Q(besluit__zaak__titel__icontains='gemeente') \
        and Q(besluit__zaak__titel__icontains='amenvoeg')) \
    .exclude(Q(besluit__zaak__titel__icontains='gemeente') \
        and Q(besluit__zaak__titel__icontains='herindeling')) \
    .exclude(besluit__zaak__titel__icontains='PbEU') \
    .exclude(besluit__zaak__titel__icontains='PbEG') \
    # .annotate(besluit__zaak__document = FilteredRelation('soort', condition=Q(besluit__zaak__kamerstukdossier__document_soort='Memorie van toelichting')))


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
