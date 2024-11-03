from django.core.management.base import BaseCommand

from infrastructure.models import Attendee, Project


class Command(BaseCommand):  # pragma: no cover
    help = "Export projects.csv and judges.csv for importing into Gavel"

    def handle(self, *args, **kwargs):  # noqa: C901        
        judging_eligible_attendees = Attendee.objects.all()
        judging_eligible_attendees_entries = []
        for attendee in judging_eligible_attendees:
            if attendee.participation_class == "J" or attendee.participation_class == 'S':
                judging_eligible_attendees_entries.append(f'"{attendee.first_name} {attendee.last_name}","{attendee.email}","{attendee.bio}"')
        projects_to_be_judged = Project.objects.all()
        projects_to_be_judged_entries = []
        for project in projects_to_be_judged:
            if hasattr(project, "team") and hasattr(project.team, "table") and hasattr(project.team.table, "number") and project.team.table.number:
                projects_to_be_judged_entries.append(f'"{project.name}","Table {project.team.table.number}","{project.description}"')
        with open("judges.csv", "w") as f:
            f.write("\n".join(judging_eligible_attendees_entries))
        with open("projects.csv", "w") as f:
            f.write("\n".join(projects_to_be_judged_entries))
