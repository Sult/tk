# All votes
votes = Stemming.objects

# Filter all votes about laws
votes = Stemming.objects.filter(besluit__zaak__soort = 'Wetgeving')

# Exclude votes that have not reached the floor
votes = Stemming.objects.exclude(besluit__stemming_soort='')

# Exclude votes about merging city councils
votes = Stemming.objects.exclude(Q(besluit__zaak__titel__icontains='gemeente') and Q(besluit__zaak__titel__icontains='amenvoeg'))

# Exclude votes about cities reorganisations
votes = Stemming.objects.exclude(Q(besluit__zaak__titel__icontains='gemeente') and Q(besluit__zaak__titel__icontains='herindeling'))

# Exclude votes about EU publications
votes = Stemming.objects.exclude(besluit__zaak__titel__icontains='PbEU')

# Combined query:
votes = Stemming.objects \
    .filter(besluit__zaak__soort = 'Wetgeving') \
    .exclude(besluit__stemming_soort='') \
    .exclude(Q(besluit__zaak__titel__icontains='gemeente') and Q(besluit__zaak__titel__icontains='amenvoeg')) \
    .exclude(Q(besluit__zaak__titel__icontains='gemeente') and Q(besluit__zaak__titel__icontains='herindeling')) \
    .exclude(besluit__zaak__titel__icontains='PbEU') \
    .exclude(besluit__zaak__titel__icontains='PbEG') \



# NOTES
# - if all parties agree the ballot is not that relevant
# - if only a few, or even just one party, vote contrarian, the ballot can be (very) relevant
