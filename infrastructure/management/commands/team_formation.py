import sqlite3
import uuid

from django.core.management.base import BaseCommand

from infrastructure.models import (Attendee, AttendeePreference, DestinyTeam,
                                   DestinyTeamAttendeeVibe, Team)


class Command(BaseCommand):  # pragma: no cover
    help = "Handle Team Formation processes through exports and imports of various SQLite3 databases."

    def add_arguments(self, parser):
        parser.add_argument("--initialize", action='store_true', required=False)
        parser.add_argument("--finalize", action='store_true', required=False)
        parser.add_argument("--import", action='store_true', required=False)
        parser.add_argument("--export", action='store_true', required=False)
    
    def handle(self, *args, **kwargs):  # noqa: C901
        if kwargs.get("initialize") and kwargs.get("finalize"):
            print("--initialize and --finalize are mutually-exclusive. Choose one.")
            exit(1)
        if kwargs.get("import") and kwargs.get("export"):
            print("--import and --export are mutually-exclusive. Choose one.")
            exit(1)
        if kwargs.get("initialize") and not (kwargs.get("import") or kwargs.get("export")):
            print("--initialize requires either --import or --export.")
            exit(1)
        if kwargs.get("finalize") and not (kwargs.get("import") or kwargs.get("export")):
            print("--finalize requires either --import or --export.")
            exit(1)
        if not kwargs.get("initialize") and not kwargs.get("finalize"):
            print("--intialize or --finalize are required.")
            exit(1)

        if kwargs.get("initialize"):
            if kwargs.get("export"):  # 1
                # serialize and export anonymized database of sqlite3 of attendees and attendee preferences
                sqlite_db_name = "initialize_export.sqlite3"
                con = sqlite3.connect(sqlite_db_name)
                self.export_attendees(con)
                self.export_attendee_preferences(con)
                con.close()
                print(f"{sqlite_db_name} saved.")
                exit(0)
                # now give the result to team_formation script
            elif kwargs.get("import"):  # 2
                # delete existing import
                DestinyTeam.objects.all().delete()
                # serialize and import three rounds of destiny teams
                sqlite_db_name = "initialize_import.sqlite3"
                con = sqlite3.connect(sqlite_db_name)
                self.import_destiny_teams(con)
                con.close()
                print(f"{sqlite_db_name} imported.")
                exit(0)
        elif kwargs.get("finalize"):
            if kwargs.get("export"):  # 4 (3 is destiny team attendee vibe scores)
                # serialize and export anonymized database of sqlite3 of attendees, attendee preferences, destiny teams, and destiny team vibe scores
                sqlite_db_name = "finalize_export.sqlite3"
                con = sqlite3.connect(sqlite_db_name)
                self.export_attendees(con)
                self.export_attendee_preferences(con)
                self.export_destiny_teams(con)
                self.export_destiny_team_vibe_scores(con)
                con.close()
                print(f"{sqlite_db_name} saved.")
                exit(0)
            elif kwargs.get("import"):  # 5
                # delete existing import
                Team.objects.all().delete()
                # serialize and import final teams
                sqlite_db_name = "finalize_import.sqlite3"
                con = sqlite3.connect(sqlite_db_name)
                self.import_teams(con)
                con.close()
                print(f"{sqlite_db_name} imported.")
                exit(0)

    def import_destiny_teams(self, con):
        cur = con.cursor()
        res = cur.execute("SELECT * FROM destinyteamattendees")
        destiny_team_attendees_by_destiny_team_id = {}
        for values in res.fetchall():
            if values[1] not in destiny_team_attendees_by_destiny_team_id:
                destiny_team_attendees_by_destiny_team_id[values[1]] = []
            destiny_team_attendees_by_destiny_team_id[values[1]].append(values[2])
        res = cur.execute("SELECT * FROM destinyteams")
        for values in res.fetchall():
            destiny_team = DestinyTeam.objects.create(id=values[0], table=values[1], track=values[2], hardware_hack=values[3], destiny_hardware=values[4], round=values[5])
            destiny_team.attendees.set(destiny_team_attendees_by_destiny_team_id[values[0]])
            destiny_team.save()

    def import_teams(self, con):
        cur = con.cursor()
        res = cur.execute("SELECT * FROM teamattendees")
        team_attendees_by_team_id = {}
        for values in res.fetchall():
            if values[1] not in team_attendees_by_team_id:
                team_attendees_by_team_id[values[1]] = []
            team_attendees_by_team_id[values[1]].append(values[2])
        res = cur.execute("SELECT * FROM teams")
        for values in res.fetchall():
            team = Team.objects.create(id=values[0], table=values[1], track=values[2], hardware_hack=values[3], destiny_hardware=values[4])
            team.attendees.set(team_attendees_by_team_id[values[0]])
            team.save()
        
    def export_attendees(self, con):
        cur = con.cursor()
        cur.execute("CREATE TABLE attendees('id', 'participation_role', 'intended_tracks', 'prefers_destiny_hardware', 'intended_hardware_hack')")
        for attendee in Attendee.objects.filter(participation_class="P"):
            if not attendee.application:
                continue
            values = [
                str(attendee.id), attendee.participation_role, ",".join(attendee.intended_tracks), ",".join(attendee.prefers_destiny_hardware), attendee.intended_hardware_hack
            ]
            print(values)
            cur.execute("""
                INSERT INTO attendees('id', 'participation_role', 'intended_tracks', 'prefers_destiny_hardware', 'intended_hardware_hack') VALUES(?, ?, ?, ?, ?)
            """, values
            )
        cur.execute("CREATE TABLE attendeepreferences('id', 'preferer', 'preferee', 'preference')")
        con.commit()
    
    def export_attendee_preferences(self, con):
        cur = con.cursor()
        for attendee_preference in AttendeePreference.objects.filter(preferer__participation_class="P"):
            if not attendee_preference.preferer.application:
                continue
            values = [
                str(attendee_preference.id), str(attendee_preference.preferer.id), str(attendee_preference.preferee.id), attendee_preference.preference
            ]
            print(values)
            cur.execute("""
                INSERT INTO attendeepreferences('id', 'preferer', 'preferee', 'preference') VALUES(?, ?, ?, ?)
            """, values
            )
        con.commit()
    
    def export_destiny_teams(self, con):
        cur = con.cursor()
        cur.execute("CREATE TABLE destinyteams('id', 'table', 'track', 'hardware_hack', 'destiny_hardware', 'round')")
        cur.execute("CREATE TABLE destinyteamattendees('id', 'destinyteam', 'destinyteamattendee')")
        for destiny_team in DestinyTeam.objects.all():
            values = [
                str(destiny_team.id), destiny_team.table, destiny_team.track, destiny_team.hardware_hack, ",".join(destiny_team.destiny_hardware), destiny_team.round
            ]
            print(values)
            cur.execute("""
                INSERT INTO destinyteams('id', 'table', 'track', 'hardware_hack', 'destiny_hardware', 'round') VALUES(?, ?, ?, ?, ?, ?)
            """, values)
            for destiny_team_attendee in destiny_team.attendees.all():
                nested_values = [
                    str(uuid.uuid4()), str(destiny_team.id), str(destiny_team_attendee.id)
                ]
                print(nested_values)
                cur.execute("""
                    INSERT INTO destinyteamattendees('id', 'destinyteam', 'destinyteamattendee') VALUES(?, ?, ?)
                """, nested_values)
        con.commit()

    def export_destiny_team_vibe_scores(self, con):
        cur = con.cursor()
        cur.execute("CREATE TABLE destinyteamattendeevibescores('id', 'destiny_team', 'attendee', 'vibe')")
        for destiny_team_attendee_vibe_score in DestinyTeamAttendeeVibe.objects.all():
            values = [
                str(destiny_team_attendee_vibe_score.id), str(destiny_team_attendee_vibe_score.destiny_team.id), str(destiny_team_attendee_vibe_score.attendee.id), destiny_team_attendee_vibe_score.vibe
            ]
            print(values)
            cur.execute("""
                INSERT INTO destinyteamattendeevibescores('id', 'destiny_team', 'attendee', 'vibe') VALUES(?, ?, ?, ?)
            """, values)
        con.commit()
