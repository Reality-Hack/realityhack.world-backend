from typing import List
from django.core.management.base import BaseCommand

from dataclasses import dataclass

from infrastructure.models import Attendee, DestinyHardware, Project, Location, Track


class Command(BaseCommand):  # pragma: no cover
    help = "Export projects.csv and judges.csv for importing into Gavel"

    def handle(self, *args, **kwargs):  # noqa: C901        
        all_projects = Project.objects.all()

        projects_to_be_judged_entries = []
        projects_excluded_entries = []
        
        for project in all_projects:
            line = to_csv_line(project)
            if is_community_hack(project):
                projects_excluded_entries.append(line)
            else:
                projects_to_be_judged_entries.append(line)
        
        with open("projects.csv", "w") as f:
            f.write("\n".join(projects_to_be_judged_entries))
        with open("projects_excluded.csv", "w") as f:
            f.write("\n".join(projects_excluded_entries))


def is_community_hack(project):
    for track in project.team.tracks:
        if track == Track.COMMUNITY_HACKS:
            return True
    return False

def to_csv_line(project):
    team = project.team

    table = team.table
    location= table.location

    uuid = ""
    name = project.name
    zone = location.building
    location = f"Table {table.number}" if zone == Location.Building.WALKER else f"{location.room}, Table {table.number}"
    tags = " ".join(get_tags(project))
    link = team.devpost_url
    description = "By {team.name}" # Not including user-submitted project description here

    # Gavel format: UUID (optional), name, zone, location, tags (space-delimited), link, description
    return f'"{uuid}","{name}","{zone}","{location}","{tags}","{link}","{description}"'


map_destiny_hardware_tag={
    DestinyHardware.META: "Meta",
    DestinyHardware.HORIZON:"Horizon",
    DestinyHardware.SNAP:"Snap",
    DestinyHardware.STYLY:"STYLY",
    DestinyHardware.SHAPESXR:"ShapesXR",
    DestinyHardware.HAPTICS:"INVALID:Haptics", #!!!
    DestinyHardware.LAMBDA:"INVALID:Lambda", #!!!
    DestinyHardware.APPLE_VISION:"VisionPro", #TODO!
    DestinyHardware.NEUROADAPTIVE: "OpenBCI",
    DestinyHardware.QUALCOMM:"Qualcomm", #TODO!
}

map_track_tag={
    Track.COMMUNITY_HACKS: "EXCLUDE:Topic:Community",
    Track.SOCIAL_XR: "Topic:Social_XR",
    Track.AUGMENTED_ENGINEERING: "Topic:AugmentedEng",
    Track.SUSTAINABILITY: "Topic:Sustainability",
    Track.AEROSPATIAL_EXPLORATION: "Topic:Aerospace",
    Track.AUGMENTED_INTELLIGENCE: "Topic:AI",
    Track.HEALTHCARE: "INVALID:Healthcare", #!!!
}

def get_tags(project):
    team = project.team
    tags = []
    for destiny_hardware in team.destiny_hardware:
        tags.append(map_destiny_hardware_tag[destiny_hardware])
    for track in team.tracks:
        tags.append(map_track_tag[track])
    if team.hardware_hack:
        tags.append("HardwareHack")
    
    return tags