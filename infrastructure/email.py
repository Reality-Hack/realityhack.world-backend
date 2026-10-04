import os

from infrastructure.utils.event_dates import format_event_date, format_event_month, get_judging_start


def _welcome_paragraph(event, *trailing_sentences):
    """'Looking forward to welcoming you' paragraph, omitting Discord copy when unset."""
    month = format_event_month(event.start_date, event.timezone)
    sentences = [f"We're looking forward to welcoming you in {month}."]
    if event.discord_url:
        sentences.append(
            f"Until then, make sure you have joined our Discord here: {event.discord_url}"
            " so that you stay up-to-date with us."
            " During the event, we will be centralizing all communications on Discord."
        )
    sentences.extend(s for s in trailing_sentences if s)
    return " ".join(sentences)


def get_hacker_application_confirmation_template(first_name, event, response_email_address="<apply@realityhackinc.org>"):
    return f"Application Confirmation for {event.name}", (
        f"Hi there {first_name},"
        "\n\n"
        f"Thank you so much for submitting your participant application to {event.name}. "
        "This email is to confirm that we have received your application."
        "\n\n"
        "Please keep an eye on your email to hear back from us regarding the status of your application. "
        f"If you have any questions regarding applications and the application process, please reply back or send an email to {response_email_address}"
        "\n\n"
        "Thank you,"
        "\n\n"
        "Reality Hack Applications Team"
    )


def get_mentor_application_confirmation_template(first_name, event, response_email_address="<apply@realityhackinc.org>"):
    return f"Mentor Interest Confirmation for {event.name}", (
        f"Hi there {first_name},"
        "\n\n"
        f"Thank you so much for submitting the Mentor Interest Form for {event.name}. "
        "This email is to confirm that we have received your submission."
        "\n\n"
        "Please keep an eye on your email to hear back from us regarding your interest. "
        " If you were specifically invited to be a mentor by our team or are part of a sponsoring company, you're all set! "
        f"If you have any questions regarding the role of a mentor at Reality Hack, please send an email to {response_email_address}!"
        "\n\n"
        "Thank you,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_judge_application_confirmation_template(first_name, event, response_email_address="<apply@realityhackinc.org>"):
    return f"Judge Interest Confirmation for {event.name}", (
        f"Hi there {first_name},"
        "\n\n"
        f"Thank you so much for submitting the Judge Interest Form for {event.name}. "
        "This email is to confirm that we have received your submission."
        "\n\n"
        "Please keep an eye on your email to hear back from us regarding your interest. "
        "If you were specifically invited to be a judge by our team or are part of a sponsoring company, you're all set! "
        f"If you have any questions regarding the role of a judge at Reality Hack, please send an email to {response_email_address}!"
        "\n\n"
        "Thank you,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_hacker_rsvp_request_template(first_name, application_id, event):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/rsvp/{application_id}"
    special_tracks = (
        "This year, in addition to the Hardware Hack, we have a couple special tracks you can indicate your interest in on the RSVP form. "
        f"Check out the tracks here: {event.special_tracks_url}"
        "\n\n"
    ) if event.special_tracks_url else ""
    rsvp_deadline = (
        f"Please submit your RSVP by {format_event_date(event.rsvp_deadline, event.timezone)}"
        " to secure your spot or we will release your spot to someone on our waitlist."
    ) if event.rsvp_deadline else ""
    return f"RSVP to {event.name} and Secure Your Spot", (
        f"Hi there {first_name},"
        "\n\n"
        f"We're so excited for you to join us as a hacker at {event.name}. At this time, please RSVP on our event portal by following this unique, personalized link to submit your RSVP to us."
        "\n\n"
        "When you get to the Discord username question, please double and triple check you've entered your correct Discord username."
        "\n\n"
        f"{request_uri}"
        "\n\n"
        "In this RSVP form, if you are 17 and under when the event begins, you'll need a parent/guardian to sign a consent form if they have not already done so. Your parent/guardian will also need to be with you at all times throughout the event."
        "\n\n"
        f"{special_tracks}"
        f"{_welcome_paragraph(event, rsvp_deadline)}"
        "\n\n"
        "Let us know on Discord if you're having issues with the RSVP or email us back at tech@realityhackinc.org!"
        "\n\n"
        "See you soon,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_mentor_rsvp_request_template(first_name, application_id, event):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/rsvp/mentor/{application_id}"
    return f"RSVP to {event.name}", (
        f"Hi there {first_name},"
        "\n\n"
        f"We're so excited for you to join as a mentor at {event.name}. At this time, please RSVP on our event portal by following this unique, personalized link to submit your RSVP to us."
        "\n\n"
        "When you get to the Discord username question, please double and triple check you've entered your correct Discord username."
        "\n\n"
        f"{request_uri}"
        "\n\n"
        f"{_welcome_paragraph(event)}"
        "\n\n"
        "Let us know on Discord if you're having issues with the RSVP or email us back at tech@realityhackinc.org!"
        "\n\n"
        "See you soon,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_judge_rsvp_request_template(first_name, application_id, event):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/rsvp/judge/{application_id}"
    judging_day = format_event_date(get_judging_start(event), event.timezone)
    return f"RSVP to {event.name}", (
        f"Hi there {first_name},"
        "\n\n"
        f"We're so excited for you to join as a judge at {event.name}. At this time, please RSVP on our event portal by following this unique, personalized link to submit your RSVP to us."
        "\n\n"
        f"{request_uri}"
        "\n\n"
        f"We're looking forward to welcoming you on judging day, {judging_day}."
        "\n\n"
        "Let us know if you're having issues with the RSVP by emailing us at tech@realityhackinc.org! Stay tuned for more communications from us regarding the schedule of the judging day."
        "\n\n"
        "See you soon,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


RSVP_EMAIL_SUBJECT = ("Thank you for your RSVP to Reality Hack"
                      " - Login to www.realityhack.world")


def get_hacker_rsvp_confirmation_template(first_name, password):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/signin"
    if password:
        password_message = (f"You can now log in to {request_uri} with"
                            f" your temporary password: {password}"
                            "\n\n"
                            "You'll be prompted to change your password immediately"
                            " after. Please change your password to something that you"
                            " can remember.")
    else:
        password_message = (f"You can now log in to {request_uri} with your existing"
                            " account.")
    return RSVP_EMAIL_SUBJECT, (
        f"Hi there {first_name},"
        "\n\n"
        f"{password_message}"
        "\n\n"
        "We'll be using our www.realityhack.world site as the main management hub"
        " for Reality Hack. "
        "During the event, you'll use the site to do a number of things including"
        " checking in, requesting hardware, and forming teams. "
        "You'll need the QR Code on the site to check-in."
        "\n\n"
        "We're looking forward to welcoming you to Reality Hack!"
        "\n\n"
        "See you soon,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_non_hacker_rsvp_confirmation_template(first_name, password):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/signin"
    if password:
        password_message = (f"You can now log in to {request_uri} with"
                            f" your temporary password: {password}"
                            "\n\n"
                            "You'll be prompted to change your password immediately"
                            " after. Please change"
                            " your password to something that you can remember.")
    else:
        password_message = (f"Welcome back! You can now log into {request_uri} "
                            "with your existing account.")
    return RSVP_EMAIL_SUBJECT, (
        f"Hi there {first_name},"
        "\n\n"
        f"{password_message}"
        " You'll need the QR Code on the site to check-in."
        "\n\n"
        "We're looking forward to welcoming you to Reality Hack!"
        "\n\n"
        "See you soon,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_multiple_users_found_template(email):
    return "Multiple users found for email", (
        f"Hi there,"
        "\n\n"
        f"We're sorry, but we found multiple users for {email}."
        " Rest assured we are working to resolve this issue."
        "\n\n"
        "Thank you,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_keycloak_account_error_template(email, error):
    return "Keycloak Account Error", (
        f"Hi there,"
        "\n\n"
        f"The following user had an error creating a Keycloak account: {email}."
        f" Error: {error}. Please rectify immediately."
        "\n\n"
        "Thank you,"
        "\n\n"
        "Reality Hack Organizing Team"
    )
