from django.db import models


class TweedeKamerMixin(object):
    id = models.UUIDField(primary_key=True)

    gewijzigd_op = models.DateTimeField(null=True, blank=True)
    api_gewijzigd_op = models.DateTimeField(blank=True, null=True)
    verwijderd = models.BooleanField()
