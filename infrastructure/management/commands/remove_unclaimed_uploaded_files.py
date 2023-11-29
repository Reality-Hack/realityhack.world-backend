from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure.models import Application, UploadedFile


class Command(BaseCommand):  # pragma: no cover
    help = "Generates test data"

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        unclaimed_files = UploadedFile.objects.all().filter(claimed=False)
        for unclaimed_file in unclaimed_files:
            unclaimed_file.delete()

