#!/usr/bin/env sh

docker run -ti -p 8000:8000 realityhack.world-backend sh -c "\
    ./manage.py migrate && \
    ./manage.py setup_test_data && \
    ./manage.py runserver 0.0.0.0:8000
"
