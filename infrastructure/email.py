def get_hacker_application_confirmation_template(first_name):
    return "Application Confirmation for MIT Reality Hack 2024", (
        f"Hi there {first_name},"
        "\n\n"
        "Thank you so much for submitting your participant application to MIT Reality Hack 2024. "
        "This email is to confirm that we have received your application."
        "\n\n"
        "Please keep an eye on your email to hear back from us regarding the status of your application. "
        "If you have any questions regarding applications and the application process, please reply back or send an email to apply@mitrealityhack.com!"
        "\n\n"
        "Thank you,"
        "\n\n"
        "MIT Reality Hack Applications Team"
    )

def get_mentor_application_confirmation_template(first_name, response_email_address="apply@mitrealityhack.com"):
    return "Mentor Interest Confirmation for MIT Reality Hack 2024", (
        f"Hi there {first_name},"
        "\n\n"
        "Thank you so much for submitting the Mentor Interest Form for MIT Reality Hack 2024. "
        "This email is to confirm that we have received your submission."
        "\n\n"
        "Please keep an eye on your email to hear back from us regarding your interest. "
        " If you were specifically invited to be a mentor by our team or are part of a sponsoring company, you're all set! "
        f"If you have any questions regarding the role of a mentor at MIT Reality Hack, please send an email to {response_email_address}!"
        "\n\n"
        "Thank you,"
        "\n\n"
        "MIT Reality Hack Organizing Team"
    )

def get_judge_application_confirmation_template(first_name, response_email_address="apply@mitrealityhack.com"):
    return "Judge Interest Confirmation for MIT Reality Hack 2024", (
        f"Hi there {first_name},"
        "\n\n"
        "Thank you so much for submitting the Judge Interest Form for MIT Reality Hack 2024. "
        "This email is to confirm that we have received your submission."
        "\n\n"
        "Please keep an eye on your email to hear back from us regarding your interest. "
        "If you were specifically invited to be a judge by our team or are part of a sponsoring company, you're all set! "
        f"If you have any questions regarding the role of a judge at MIT Reality Hack, please send an email to {response_email_address}!"
        "\n\n"
        "Thank you,"
        "\n\n"
        "MIT Reality Hack Organizing Team"
    )
