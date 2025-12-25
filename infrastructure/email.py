import os


def get_hacker_application_confirmation_template(first_name, response_email_address="<apply@realityhackinc.org>"):
    return "Application Confirmation for Reality Hack at MIT 2026", (
        f"Hi there {first_name},"
        "\n\n"
        "Thank you so much for submitting your participant application to Reality Hack 2026. "
        "This email is to confirm that we have received your application."
        "\n\n"
        "Please keep an eye on your email to hear back from us regarding the status of your application. "
        f"If you have any questions regarding applications and the application process, please reply back or send an email to {response_email_address}"
        "\n\n"
        "Thank you,"
        "\n\n"
        "Reality Hack Applications Team"
    )


def get_mentor_application_confirmation_template(first_name, response_email_address="<apply@realityhackinc.org>"):
    return "Mentor Interest Confirmation for Reality Hack at MIT 2026", (
        f"Hi there {first_name},"
        "\n\n"
        "Thank you so much for submitting the Mentor Interest Form for Reality Hack 2026. "
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


def get_judge_application_confirmation_template(first_name, response_email_address="<apply@realityhackinc.org>"):
    return "Judge Interest Confirmation for Reality Hack at MIT 2026", (
        f"Hi there {first_name},"
        "\n\n"
        "Thank you so much for submitting the Judge Interest Form for Reality Hack 2026. "
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

def get_hacker_rsvp_request_template(first_name, application_id):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/rsvp/{application_id}"
    return "RSVP to Reality Hack at MIT 2026 and Secure Your Spot", (
        f"Hi there {first_name},"
        "\n\n"
        "We're so excited for you to join us as a hacker at Reality Hack at MIT 2026. At this time, please RSVP on our event portal by following this unique, personalized link to submit your RSVP to us."
        "\n\n"
        "When you get to the Discord username question, please double and triple check you've entered your correct Discord username."
        "\n\n"
        f"{request_uri}"
        "\n\n"
        "In this RSVP form, if you are 17 and under when the event begins, you'll need a parent/guardian to sign a consent form if they have not already done so. Your parent/guardian will also need to be with you at all times throughout the event."
        "\n\n"
        "This year, in addition to the Hardware Hack, we have a couple special tracks you can indicate your interest in on the RSVP form. Check out the tracks here: https://www.realityhackatmit.com/2026-special-tracks"
        "\n\n"
        "We're looking forward to welcoming you in January. Until then, make sure you have joined our Discord here: https://discord.gg/XfDXqwTPfv so that you stay up-to-date with us. During the event, we will be centralizing all communications on Discord. Please submit your RSVP by December 30, 2025 to secure your spot or we will release your spot to someone on our waitlist."
        "\n\n"
        "Let us know on Discord if you're having issues with the RSVP or email us back at tech@realityhackinc.org!"
        "\n\n"
        "See you soon,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_mentor_rsvp_request_template(first_name, application_id):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/rsvp/mentor/{application_id}"
    return "RSVP to Reality Hack at MIT 2026", (
        f"Hi there {first_name},"
        "\n\n"
        "We're so excited for you to join as a mentor at Reality Hack at MIT 2026. At this time, please RSVP on our event portal by following this unique, personalized link to submit your RSVP to us."
        "\n\n"
        "When you get to the Discord username question, please double and triple check you've entered your correct Discord username."
        "\n\n"
        f"{request_uri}"
        "\n\n"
        "We're looking forward to welcoming you in January. Until then, make sure you have joined our Discord here: https://discord.gg/XfDXqwTPfv so that you stay up-to-date with us. During the event, we will be centralizing all communications on Discord."
        "\n\n"
        "Let us know on Discord if you're having issues with the RSVP or email us back at tech@realityhackinc.org!"
        "\n\n"
        "See you soon,"
        "\n\n"
        "Reality Hack Organizing Team"
    )


def get_judge_rsvp_request_template(first_name, application_id):
    frontend_domain = os.environ["FRONTEND_DOMAIN"]
    request_uri = f"{frontend_domain}/rsvp/judge/{application_id}"
    return "RSVP to Reality Hack at MIT 2026", (
        f"Hi there {first_name},"
        "\n\n"
        "We're so excited for you to join as a judge at Reality Hack at MIT 2026. At this time, please RSVP on our event portal by following this unique, personalized link to submit your RSVP to us."
        "\n\n"
        f"{request_uri}"
        "\n\n"
        "We're looking forward to welcoming you in January."
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
