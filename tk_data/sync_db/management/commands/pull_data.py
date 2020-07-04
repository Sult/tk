import logging
from django.core.management.base import BaseCommand

from sync_db.api import sync
from sync_db.models import Feed, Entry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "pull new data from tweedekamer opendata"

    def handle(self, *args, **options):
        # get last feed that has a next set.
        logger.info("Pulling data")
        for feed in Feed.objects.all().order_by('-pk'):
            if feed.next:
                sync(feed.next)
                break

        # try fixing bugged objects
        logger.info("rerun failed saved entries")
        for entry in Entry.objects.filter(saved=False):
            entry.save()

