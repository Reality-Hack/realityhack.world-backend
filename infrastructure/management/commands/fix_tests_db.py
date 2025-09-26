from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):  # pragma: no cover
    help = "Clear concurrent connections to the tests database"

    def handle(self, *args, **kwargs):  # noqa: C901
        cursor = connection.cursor()
        database_name = 'test_django'
        cursor.execute(
            "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity "
            "WHERE pg_stat_activity.datname = %s AND pid <> pg_backend_pid();",
            [database_name],
        )
