from django.core.management.base import BaseCommand

from portal import models


class Command(BaseCommand):
    help = "Removes orphaned private files"

    # def add_arguments(self, parser):
    #     parser.add_argument('sample', nargs='+')

    def handle(self, *args, **options):
        models.clean_private_fils()
