from itertools import zip_longest

from django.db import transaction
from django.core.management.base import BaseCommand

from infrastructure.models import DestinyTeam, Table, Track


class Command(BaseCommand):  # pragma: no cover
    help = "Assign tables to destiny teams"
    
    def add_arguments(self, parser):
        parser.add_argument("--round", type=int, required=True, help="Round to assign tables for")

    def table_range(self, start, end):
        return Table.objects.filter(
            **(dict(number__gte=start) if start is not None else dict()),
            **(dict(number__lte=end) if end is not None else dict())
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        teams = DestinyTeam.objects.filter(round=kwargs["round"])
        print("Total number of teams:", teams.count(),
              "Total number of tables:", Table.objects.count())
        
        future_constructors = self.table_range(1, 19)
        learning = self.table_range(20, 38)
        productivity = self.table_range(39, 57)
        living_harmony = self.table_range(58, 68).union(self.table_range(93, 100))
        vitality = self.table_range(69, 72).union(self.table_range(78, 92))
        community = self.table_range(73, 77)
        track_to_tables = {
            Track.FUTURE_CONSTRUCTORS: future_constructors,
            Track.LEARNING: learning,
            Track.WORK: productivity,
            Track.HEALTH: vitality,
            Track.SMART_CITIES: living_harmony,
            Track.COMMUNITY_HACKS: community,
        }
        print("Tables assigned to tracks:", sum(v.count() for v in track_to_tables.values()))
        
        print("Assigning tables...")
        spare_teams = []
        spare_tables = self.table_range(101, None).all()
        for track, tables in track_to_tables.items():
            track_teams = teams.filter(track=track)
            for team, table in zip_longest(track_teams, tables):
                if team is None:
                    spare_tables.append(table)
                elif table is None:
                    spare_teams.append(team)
                else:
                    team.table = table
                    team.save()
        print("Spare teams:", len(spare_teams), "Spare tables:", len(spare_tables))
        assert len(spare_teams) <= len(spare_tables)
        for team, table in zip_longest(spare_teams, spare_tables):
            team.table = table
            team.save()
