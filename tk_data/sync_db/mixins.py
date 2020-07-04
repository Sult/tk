import uuid
import copy
import logging

import requests
from dateutil.parser import parse as parse_date
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType

from django.contrib.postgres.fields import JSONField
from django.db import models

logger = logging.getLogger(__name__)


class TweedeKamerMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = JSONField(default=dict)
    saved_related = models.BooleanField(default=True)
    bugged = GenericRelation('sync_db.BuggedModel')

    gewijzigd_op = models.DateTimeField(null=True, blank=True)
    api_gewijzigd_op = models.DateTimeField(blank=True, null=True)
    verwijderd = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        parsed_data = kwargs.pop('parsed_data', None)
        if kwargs.pop('parse_data', True):
            if not parsed_data:
                parsed_data = self.parse_entry_data()

            for key, value in parsed_data.items():
                setattr(self, key, value)

        super().save(*args, **kwargs)

    @classmethod
    def create_from_json(cls, data):
        """ use this method on response data from a direct openapi call instead of sync """

        fields = cls._meta.get_fields()
        parsed_data = {}
        for field in fields:
            key = cls.get_key_name(field.name)
            if isinstance(field, models.ForeignKey) and data.get(key):
                try:
                    parsed[field.name] = field.related_model.objects.get(id=content[key]['@ref'])
                except field.related_model.DoesNotExist as exc:
                    parsed[field.name] = None
                    parsed['saved_related'] = False
                    self.mark_bugged(str(exc))
                    logger.error('Couldnt not find related object(%) for %s',
                                 field.related_model.__name__, self.__class__.__name__)





    def mark_bugged(self, error):
        """ create bugged related object """

        from sync_db.models import BuggedModel
        if not BuggedModel.objects.filter(
                content_type=ContentType.objects.get_for_model(self.__class__), object_id=self.id).exists():
            BuggedModel.objects.create(content_object=self)

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

    def parse_entry_data(self):
        # always should be an id
        content = copy.deepcopy(self.rename_namespace(self.data['content'])[self.data['category']['@term']])
        parsed = {}

        content = self.rename_namespace(content)
        fields = self._meta.get_fields()
        for field in fields:
            key = self.get_key_name(field.name)
            if isinstance(field, models.ForeignKey) and content.get(key):
                try:
                    parsed[field.name] = field.related_model.objects.get(id=content[key]['@ref'])
                except field.related_model.DoesNotExist as exc:
                    parsed[field.name] = None
                    parsed['saved_related'] = False
                    self.mark_bugged(str(exc))
                    logger.error('Couldnt not find related object(%) for %s',
                                 field.related_model.__name__, self.__class__.__name__)

                    import json
                    with open('missing.json', 'r') as f:
                        missing = json.loads(f.read())

                    model_name = field.related_model.__name__
                    if model_name not in missing:
                        missing[model_name] = []

                    keys = set(missing[model_name])
                    keys.add(content[key]['@ref'])
                    missing[model_name] = list(keys)

                    with open('missing.json', 'w') as f:
                        f.write(json.dumps(missing, indent=2))

            elif key in content:
                if content[key] == {'@xsi:nil': 'true'}:
                    parsed[field.name] = None
                else:
                    if isinstance(field, models.DateTimeField):
                        parsed[field.name] = parse_date(content[key])
                    elif isinstance(field, (models.BooleanField, models.NullBooleanField)):
                        # null is already set when content[key] == {'@xsi:nil': 'true'}
                        parsed[field.name] = content[key] == 'true'
                    else:
                        parsed[field.name] = content[key]

        parsed['api_gewijzigd_op'] = None
        parsed['verwijderd'] = content.get('@tk:verwijderd') == 'true'
        if content.get('@tk:bijgewerkt'):
            parsed['gewijzigd_op'] = parse_date(content.get('@tk:bijgewerkt'))

        return parsed

