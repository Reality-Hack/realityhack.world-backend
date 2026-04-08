from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pycountry
from django.core.management.base import BaseCommand

from infrastructure.utils.csv_export import (
    choice_label,
    parse_multiselect_values,
    write_csv,
)
from infrastructure.models import (
    Application,
    Event,
    EventRsvp,
    ParticipationClass,
    ParticipationRole,
    ParticipationCapacity,
    Team,
)


class Command(BaseCommand):
    help = "Export comprehensive event statistics to a text report"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="exports",
            help="Directory to save report (default: exports)"
        )
        parser.add_argument(
            "--output-file",
            default="event_statistics_report.txt",
            help=(
                "Report filename "
                "(default: event_statistics_report.txt)"
            )
        )
        parser.add_argument(
            "--us-participants-csv",
            default="us_participants_for_state_processing.csv",
            help=(
                "CSV filename for US participants "
                "(default: us_participants_for_state_processing.csv)"
            )
        )

    def handle(self, *args, **options):
        # Get the active event
        event = Event.get_active()
        if not event:
            self.stderr.write(self.style.ERROR("No active event found"))
            return

        self.stdout.write(f"Generating statistics for event: {event.name}")

        # Setup output directory
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / options["output_file"]
        us_csv_path = output_dir / options["us_participants_csv"]

        # Initialize statistics structure
        stats = self._initialize_stats()

        # Query applications
        self._collect_application_stats(event, stats)

        # Query and process EventRsvps
        self._collect_rsvp_stats(event, stats)

        # Calculate team role distributions
        self._collect_team_role_stats(event, stats)

        # Generate and write report
        report_content = self._format_report(event, stats)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        # Export US participants list
        self._export_us_participants(us_csv_path, stats)

        # Summary
        self.stdout.write(self.style.SUCCESS("\nExport complete!"))
        self.stdout.write(f"  Report saved to: {report_path}")
        self.stdout.write(f"  US participants list saved to: {us_csv_path}")

    def _initialize_stats(self) -> dict:
        """Initialize all statistics counters and collections."""
        return {
            'applications': {
                'total': 0,
                'participants': 0,
                'mentors': 0,
                'judges': 0,
            },
            'checked_in_participants': 0,
            'participation_class': defaultdict(int),
            'participation_class_checked_in': defaultdict(int),
            'nationalities': defaultdict(int),
            'current_countries': defaultdict(int),
            'international_travelers': 0,
            'us_domestic': 0,
            'us_participants': [],  # For CSV export
            'career_stage': defaultdict(int),
            'employer': defaultdict(int),
            'industry': defaultdict(int),
            'gender_identity': defaultdict(int),
            'gender_identity_other': set(),
            'age_groups': defaultdict(int),
            'race_ethnic_groups': defaultdict(int),
            'race_ethnic_other': set(),
            'participation_roles': defaultdict(int),
            'previously_participated': 0,
            'not_previously_participated': 0,
            'previous_years': defaultdict(int),
            'schools': defaultdict(int),
            'heard_about_us': defaultdict(int),
            'heard_about_us_other': set(),
            'missing_application_warnings': [],
            'team_roles': {},  # team_id -> role_counts
        }

    def _collect_application_stats(self, event: Event, stats: dict) -> None:
        """Query and count applications by participation class."""
        applications = Application.objects.for_event(event)
        stats['applications']['total'] = applications.count()
        stats['applications']['participants'] = applications.filter(
            participation_class=ParticipationClass.PARTICIPANT
        ).count()
        stats['applications']['mentors'] = applications.filter(
            participation_class=ParticipationClass.MENTOR
        ).count()
        stats['applications']['judges'] = applications.filter(
            participation_class=ParticipationClass.JUDGE
        ).count()

    def _collect_rsvp_stats(self, event: Event, stats: dict) -> None:
        """Query EventRsvps and collect all metrics in a single pass."""
        rsvps = EventRsvp.objects.for_event(event).select_related(
            'attendee', 'application'
        )

        for rsvp in rsvps:
            # Count by participation class
            stats['participation_class'][rsvp.participation_class] += 1
            if rsvp.checked_in_at:
                pc = rsvp.participation_class
                stats['participation_class_checked_in'][pc] += 1

            # Process participant demographics (checked-in only)
            is_participant = (
                rsvp.participation_class == ParticipationClass.PARTICIPANT
            )
            if is_participant and rsvp.checked_in_at:
                stats['checked_in_participants'] += 1
                self._process_participant_demographics(rsvp, stats)

    def _process_participant_demographics(
        self, rsvp: EventRsvp, stats: dict
    ) -> None:
        """Process demographics for a single checked-in participant."""
        application = rsvp.application

        if not application:
            stats['missing_application_warnings'].append({
                'attendee_id': str(rsvp.attendee.id),
                'first_name': rsvp.attendee.first_name,
                'last_name': rsvp.attendee.last_name,
                'email': rsvp.attendee.email,
            })
            return

        self._process_nationality(application, stats)
        self._process_current_country(application, rsvp, stats)
        self._process_gender_identity(application, stats)
        self._process_age_group(application, stats)
        self._process_race_ethnicity(application, stats)
        self._process_participation_role(application, stats)
        self._process_previous_participation(application, stats)
        self._process_school(application, stats)
        self._process_outreach(application, stats)
        self._process_career_stage(application, stats)
        self._process_employer_industry(application, stats)

    def _process_nationality(
        self, application: Application, stats: dict
    ) -> None:
        """Process nationality field."""
        if application.nationality:
            nationalities = self._parse_multiselect_field(
                application.nationality
            )
            for country_code in nationalities:
                stats['nationalities'][country_code] += 1

    def _process_career_stage(
        self, application: Application, stats: dict
    ) -> None:
        """Process participation capacity (career stage) field."""
        if application.participation_capacity:
            stats['career_stage'][application.participation_capacity] += 1

    def _process_employer_industry(
        self, application: Application, stats: dict
    ) -> None:
        """Process employer field."""
        if application.employer:
            stats['employer'][application.employer] += 1
        if application.industry:
            industries = self._parse_multiselect_field(
                application.industry
            )
            for industry in industries:
                stats['industry'][industry] += 1

    def _process_current_country(
        self, application: Application, rsvp: EventRsvp, stats: dict
    ) -> None:
        """Process current country and travel origin."""
        if not application.current_country:
            return

        current_countries = self._parse_multiselect_field(
            application.current_country
        )
        for country_code in current_countries:
            stats['current_countries'][country_code] += 1

        if 'US' in current_countries:
            stats['us_domestic'] += 1
            stats['us_participants'].append({
                'attendee_id': str(rsvp.attendee.id),
                'first_name': application.first_name,
                'last_name': application.last_name,
                'email': application.email,
                'current_city': application.current_city or '',
            })
        else:
            stats['international_travelers'] += 1

    def _process_gender_identity(
        self, application: Application, stats: dict
    ) -> None:
        """Process gender identity field."""
        if application.gender_identity:
            genders = self._parse_multiselect_field(
                application.gender_identity
            )
            for gender in genders:
                stats['gender_identity'][gender] += 1
        if application.gender_identity_other:
            stats['gender_identity_other'].add(
                application.gender_identity_other
            )

    def _process_age_group(
        self, application: Application, stats: dict
    ) -> None:
        """Process age group field."""
        if application.age_group:
            stats['age_groups'][application.age_group] += 1

    def _process_race_ethnicity(
        self, application: Application, stats: dict
    ) -> None:
        """Process race/ethnicity field."""
        if application.race_ethnic_group:
            races = self._parse_multiselect_field(
                application.race_ethnic_group
            )
            for race in races:
                stats['race_ethnic_groups'][race] += 1
        if application.race_ethnic_group_other:
            stats['race_ethnic_other'].add(
                application.race_ethnic_group_other
            )

    def _process_participation_role(
        self, application: Application, stats: dict
    ) -> None:
        """Process participation role field."""
        if application.participation_role:
            stats['participation_roles'][
                application.participation_role
            ] += 1

    def _process_previous_participation(
        self, application: Application, stats: dict
    ) -> None:
        """Process previous participation field."""
        if application.previously_participated:
            stats['previously_participated'] += 1
            if application.previous_participation:
                years = self._parse_multiselect_field(
                    application.previous_participation
                )
                for year in years:
                    stats['previous_years'][year] += 1
        else:
            stats['not_previously_participated'] += 1

    def _process_school(
        self, application: Application, stats: dict
    ) -> None:
        """Process school field."""
        if application.student_school:
            stats['schools'][application.student_school] += 1

    def _process_outreach(
        self, application: Application, stats: dict
    ) -> None:
        """Process outreach/heard about us field."""
        if application.heard_about_us:
            methods = self._parse_multiselect_field(
                application.heard_about_us
            )
            for method in methods:
                stats['heard_about_us'][method] += 1
        if application.heard_about_us_other:
            stats['heard_about_us_other'].add(
                application.heard_about_us_other
            )

    def _collect_team_role_stats(self, event: Event, stats: dict) -> None:
        """Calculate role distribution per team for checked-in."""
        teams = Team.objects.for_event(event).prefetch_related(
            'attendees'
        )

        for team in teams:
            team_roles = defaultdict(int)
            team_attendees = team.attendees.all()
            rsvps = EventRsvp.objects.for_event(event).filter(
                attendee__in=team_attendees,
            ).select_related('application').all()
            for rsvp in rsvps:
                try:
                    participation_role = rsvp.application.participation_role
                    team_roles[participation_role] += 1
                except Exception:
                    print(f"Error getting participation role for"
                          f"{rsvp.attendee.first_name} {rsvp.attendee.last_name}")
            if team_roles:
                stats['team_roles'][str(team.id)] = {
                    'team_name': team.name,
                    'team_number': team.number,
                    'roles': dict(team_roles)
                }

    def _append_report_header(self, lines: list[str], event: Event) -> None:
        lines.append("=" * 70)
        lines.append("EVENT STATISTICS REPORT")
        lines.append(f"Event: {event.name}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")

    def _append_applications_received(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("1. APPLICATIONS RECEIVED")
        lines.append(f"   Total Applications: {stats['applications']['total']:,}")
        lines.append("")
        lines.append("   Breakdown by Type:")
        total_apps = stats['applications']['total']
        if total_apps > 0:
            p_count = stats['applications']['participants']
            p_pct = self._format_percentage(p_count, total_apps)
            lines.append(f"   - Participants: {p_count:,} ({p_pct})")

            m_count = stats['applications']['mentors']
            m_pct = self._format_percentage(m_count, total_apps)
            lines.append(f"   - Mentors: {m_count:,} ({m_pct})")

            j_count = stats['applications']['judges']
            j_pct = self._format_percentage(j_count, total_apps)
            lines.append(f"   - Judges: {j_count:,} ({j_pct})")
        lines.append("")

    def _append_check_in_statistics(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("2. CHECK-IN STATISTICS")
        checked_in = stats['checked_in_participants']
        lines.append(f"   Hackers Checked In: {checked_in:,}")
        lines.append("")

        pc_class = stats['participation_class']
        pc_checked = stats['participation_class_checked_in']
        judge_rsvps = pc_class.get(ParticipationClass.JUDGE, 0)
        mentor_rsvps = pc_class.get(ParticipationClass.MENTOR, 0)
        judge_checked_in = pc_checked.get(ParticipationClass.JUDGE, 0)
        mentor_checked_in = pc_checked.get(ParticipationClass.MENTOR, 0)

        total_estimate = checked_in + judge_rsvps + mentor_rsvps
        lines.append(f"   Total Attendees Estimate: {total_estimate:,}")
        lines.append(f"   - Checked-in Participants: {checked_in:,}")
        judge_not_checked = judge_rsvps - judge_checked_in
        lines.append(
            f"   - Judge RSVPs: {judge_rsvps:,} "
            f"({judge_not_checked} not checked in)"
        )
        mentor_not_checked = mentor_rsvps - mentor_checked_in
        lines.append(
            f"   - Mentor RSVPs: {mentor_rsvps:,} "
            f"({mentor_not_checked} not checked in)"
        )
        lines.append("")

    def _append_attendees_by_participation_class(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("3. ATTENDEES BY PARTICIPATION CLASS")
        ordered = [
            (ParticipationClass.ORGANIZER, "Organizers"),
            (ParticipationClass.VOLUNTEER, "Event Volunteers"),
            (ParticipationClass.JUDGE, "Judges"),
            (ParticipationClass.MENTOR, "Non-sponsor Mentors"),
            (ParticipationClass.SPONSOR, "Sponsor Representatives"),
        ]
        for pc_code, label in ordered:
            count = stats['participation_class'].get(pc_code, 0)
            lines.append(f"   - {label}: {count:,}")

        participant_count = stats['checked_in_participants']
        lines.append(
            "   - Participants (checked-in only): "
            f"{participant_count:,}"
        )
        lines.append("")

    def _append_nationality_distribution(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Nationality Distribution:")
        if stats['nationalities']:
            sorted_nationalities = sorted(
                stats['nationalities'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for country_code, count in sorted_nationalities:
                country = self._get_country_name(country_code)
                lines.append(f"   - {country}: {count:,}")
        else:
            lines.append("   - No nationality data available")
        lines.append("")

    def _append_travel_origin_and_non_us_countries(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Travel Origin:")
        lines.append(
            f"   - International (traveling from outside US): "
            f"{stats['international_travelers']:,}"
        )
        lines.append(f"   - Domestic US: {stats['us_domestic']:,}")
        non_us_countries = [
            (code, cnt) for code, cnt in stats['current_countries'].items()
            if code != 'US'
        ]
        lines.append("")
        if non_us_countries:
            sorted_non_us = sorted(
                non_us_countries,
                key=lambda x: x[1],
                reverse=True,
            )
            lines.append("   Countries outside US (current residence):")
            for country_code, count in sorted_non_us:
                country_name = self._get_country_name(country_code)
                lines.append(f"     - {country_name}: {count:,}")
        lines.append("")

    def _append_us_state_breakdown_note(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   US State Breakdown:")
        us_count = len(stats['us_participants'])
        lines.append(
            f"   - See separate CSV file for {us_count} US participants"
        )
        lines.append(
            "     (requires manual state categorization from city field)"
        )
        lines.append("")

    def _append_gender_distribution(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Gender Distribution:")
        if stats['gender_identity']:
            sorted_genders = sorted(
                stats['gender_identity'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for gender_code, count in sorted_genders:
                label = self._get_choice_label(
                    Application.GenderIdentities.choices, gender_code
                )
                lines.append(f"   - {label}: {count:,}")
            if stats['gender_identity_other']:
                other_list = ', '.join(
                    sorted(stats['gender_identity_other'])
                )
                lines.append(f"   - Other responses: {other_list}")
        else:
            lines.append("   - No gender data available")
        lines.append("")

    def _append_age_distribution(self, lines: list[str], stats: dict) -> None:
        lines.append("   Age Distribution:")
        if stats['age_groups']:
            sorted_ages = sorted(
                stats['age_groups'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for age_code, count in sorted_ages:
                label = self._get_choice_label(
                    Application.AgeGroup.choices, age_code
                )
                lines.append(f"   - {label}: {count:,}")
        else:
            lines.append("   - No age data available")
        lines.append("")

    def _append_racial_distribution(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Racial/Ethnic Distribution:")
        if stats['race_ethnic_groups']:
            sorted_races = sorted(
                stats['race_ethnic_groups'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for race_code, count in sorted_races:
                label = self._get_choice_label(
                    Application.RaceEthnicGroups.choices, race_code
                )
                lines.append(f"   - {label}: {count:,}")
            if stats['race_ethnic_other']:
                other_list = ', '.join(
                    sorted(stats['race_ethnic_other'])
                )
                lines.append(f"   - Other responses: {other_list}")
        else:
            lines.append("   - No race/ethnicity data available")
        lines.append("")

    def _append_demographics_section(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("4. DEMOGRAPHICS (CHECKED-IN HACKERS ONLY)")
        lines.append("")
        self._append_nationality_distribution(lines, stats)
        self._append_travel_origin_and_non_us_countries(lines, stats)
        self._append_us_state_breakdown_note(lines, stats)
        self._append_gender_distribution(lines, stats)
        self._append_age_distribution(lines, stats)
        self._append_racial_distribution(lines, stats)

    def _append_team_role_distribution_aggregate(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Team Role Distribution (Aggregate):")
        if stats['participation_roles']:
            sorted_roles = sorted(
                stats['participation_roles'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            total_roles = sum(stats['participation_roles'].values())
            for role_code, count in sorted_roles:
                label = self._get_choice_label(ParticipationRole.choices, role_code)
                pct = self._format_percentage(count, total_roles)
                lines.append(f"   - {label}: {count:,} ({pct})")
        else:
            lines.append("   - No role data available")
        lines.append("")

    def _append_career_stage_distribution(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Career Stage:")
        if stats['career_stage']:
            sorted_career_stage = sorted(
                stats['career_stage'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            total_career = sum(stats['career_stage'].values())
            for career_stage_code, count in sorted_career_stage:
                label = self._get_choice_label(
                    ParticipationCapacity.choices,
                    career_stage_code,
                )
                pct = self._format_percentage(count, total_career)
                lines.append(f"   - {label}: {count:,} ({pct})")
        else:
            lines.append("   - No participation capacity data available")
        lines.append("")

    def _append_previous_participation(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Previous Participation:")
        returning = stats['previously_participated']
        lines.append(f"   - Returning participants: {returning:,}")
        new_count = stats['not_previously_participated']
        lines.append(f"   - New to Reality Hack: {new_count:,}")
        if stats['previous_years']:
            lines.append("   - Previous years attended:")
            sorted_years = sorted(
                stats['previous_years'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for year_code, count in sorted_years:
                label = self._get_choice_label(
                    Application.PreviousParticipation.choices, year_code
                )
                lines.append(f"     - {label}: {count:,}")
        lines.append("")

    def _append_school_distribution(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Schools (All):")
        if stats['schools']:
            sorted_schools = sorted(
                stats['schools'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            single_attendee_schools = [
                name for name, cnt in sorted_schools if cnt == 1
            ]
            multi_attendee_schools = [
                (name, cnt) for name, cnt in sorted_schools if cnt > 1
            ]
            for school, count in multi_attendee_schools:
                lines.append(f"   - {school}: {count:,}")
            if single_attendee_schools:
                schools_list = ", ".join(single_attendee_schools)
                lines.append(
                    "   The following schools have one participant: "
                    f"{schools_list}."
                )
        else:
            lines.append("   - No school data available")
        lines.append("")

    def _append_employer_distribution(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Employer:")
        if stats['employer']:
            sorted_employers = sorted(
                stats['employer'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for employer, count in sorted_employers:
                lines.append(f"   - {employer}: {count:,}")
        else:
            lines.append("   - No employer data available")
        lines.append("")

    def _append_industry_distribution(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("   Industry:")
        if stats['industry']:
            sorted_industries = sorted(
                stats['industry'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for industry, count in sorted_industries:
                lines.append(f"   - {industry}: {count:,}")
        else:
            lines.append("   - No industry data available")
        lines.append("")

    def _append_outreach_methods_section(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append(
            "   Outreach Methods "
            "(How did hackers hear about Reality Hack?):"
        )
        if stats['heard_about_us']:
            sorted_methods = sorted(
                stats['heard_about_us'].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for method_code, count in sorted_methods:
                label = self._get_choice_label(
                    Application.HeardAboutUs.choices, method_code
                )
                lines.append(f"   - {label}: {count:,}")
        else:
            lines.append("   - No outreach data available")
        lines.append("")

        lines.append("   List of 'Other' Outreach Methods:")
        if stats['heard_about_us_other']:
            for method in sorted(stats['heard_about_us_other']):
                lines.append(f"   - {method}")
        else:
            lines.append("   - No other methods specified")
        lines.append("")

    def _append_experience_background_section(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("5. EXPERIENCE & BACKGROUND")
        lines.append("")
        self._append_team_role_distribution_aggregate(lines, stats)
        self._append_career_stage_distribution(lines, stats)
        self._append_previous_participation(lines, stats)
        self._append_school_distribution(lines, stats)
        self._append_employer_distribution(lines, stats)
        self._append_industry_distribution(lines, stats)
        self._append_outreach_methods_section(lines, stats)

    def _append_team_roles_per_team_section(
        self, lines: list[str], stats: dict
    ) -> None:
        lines.append("6. TEAM ROLE DISTRIBUTION (PER-TEAM)")
        lines.append("")
        if stats['team_roles']:
            sorted_teams = sorted(
                stats['team_roles'].items(),
                key=lambda x: (
                    x[1]['team_number'] if x[1]['team_number'] else 9999
                ),
            )
            for team_id, team_data in sorted_teams:
                team_name = team_data['team_name']
                team_number = team_data['team_number']
                roles = team_data['roles']

                lines.append(f"   Team #{team_number}: {team_name}")
                sorted_roles = sorted(
                    roles.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                for role_code, count in sorted_roles:
                    label = self._get_choice_label(
                        ParticipationRole.choices, role_code
                    )
                    lines.append(f"     - {label}: {count}")
                lines.append("")
        else:
            lines.append("   - No team role data available")
        lines.append("")

    def _append_warnings_section(
        self, lines: list[str], stats: dict
    ) -> None:
        if not stats['missing_application_warnings']:
            return

        lines.append("=" * 70)
        lines.append("DATA QUALITY WARNINGS")
        lines.append("=" * 70)
        lines.append("")
        warning_count = len(stats['missing_application_warnings'])
        lines.append(
            f"The following {warning_count} checked-in participants"
        )
        lines.append("are missing application data:")
        lines.append("")
        for warning in stats['missing_application_warnings']:
            lines.append(f"   Attendee ID: {warning['attendee_id']}")
            first = warning['first_name']
            last = warning['last_name']
            lines.append(f"   Name: {first} {last}")
            lines.append(f"   Email: {warning['email']}")
            lines.append("")

    def _format_report(self, event: Event, stats: dict) -> str:
        """Format all statistics into a readable text report."""
        lines: list[str] = []
        self._append_report_header(lines, event)
        self._append_applications_received(lines, stats)
        self._append_check_in_statistics(lines, stats)
        self._append_attendees_by_participation_class(lines, stats)
        self._append_demographics_section(lines, stats)
        self._append_experience_background_section(lines, stats)
        self._append_team_roles_per_team_section(lines, stats)
        self._append_warnings_section(lines, stats)
        return "\n".join(lines)

    def _export_us_participants(
        self, csv_path: Path, stats: dict
    ) -> None:
        """Export US participants list for manual state processing."""
        if not stats['us_participants']:
            return

        fieldnames = ['attendee_id', 'first_name', 'last_name', 'email', 'current_city']
        write_csv(csv_path, fieldnames, stats['us_participants'])

    def _parse_multiselect_field(self, value) -> list:
        return parse_multiselect_values(value)

    def _get_choice_label(self, choices, key: str) -> str:
        return choice_label(choices, key)

    def _get_country_name(self, country_code: str) -> str:
        """Get country name from ISO country code."""
        try:
            country = pycountry.countries.get(alpha_2=country_code)
            return country.name if country else country_code
        except Exception:
            return country_code

    def _format_percentage(self, count: int, total: int) -> str:
        """Format count as percentage."""
        if total == 0:
            return "0.0%"
        return f"{(count / total * 100):.1f}%"
