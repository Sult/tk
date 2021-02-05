import uuid
import copy
import logging
import requests
from dateutil.parser import parse as parse_date
from django.db import models

logger = logging.getLogger(__name__)


class TweedeKamerMixin(models.Model):
    DATA_URL = 'https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/%s/%s'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.JSONField(default=dict)

    gewijzigd_op = models.DateTimeField(null=True, blank=True)
    api_gewijzigd_op = models.DateTimeField(blank=True, null=True)
    verwijderd = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def get_related_obj(self, field, content):
        """ get related object from db, or pull from api otherwise """

        try:
            return field.related_model.objects.get(id=content[self.get_key_name(field.name)]['@ref'])
        except field.related_model.DoesNotExist:
            response = requests.get(self.DATA_URL % (field.name, content[field.name]['@ref']))
            obj = field.related_model.create_from_json(response.json())
            return obj

    @classmethod
    def create_from_json(cls, data):
        """ use this method on response data from a direct openapi call instead of sync """

        fields = cls._meta.get_fields()
        parsed_data = {}
        for field in fields:
            key = cls.get_key_name(field.name)
            if isinstance(field, models.ForeignKey) and data.get(key):
                try:
                    parsed_data[field.name] = field.related_model.objects.get(id=data[key]['@ref'])
                except field.related_model.DoesNotExist as exc:
                    breakpoint()
                    raise

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
