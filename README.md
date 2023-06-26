# Infrastructure for Reality Hack 2024

## Setup

### Local

#### Basic setup

```shell
pip install -r requirements.txt
python manage.py migrate
```

#### Create fake test data

```shell
python manage.py setup_test_data
```

#### Get API schema spec

```shell
python manage.py spectacular --file schema.yml
```

#### Run tests

```shell
./test
```

##### Show test coverage

```
coverage report
```

#### Run server

```shell
python manage.py runserver
```

### Cloud

This server and database are deployed using Google Cloud. The guide to deploying with AppEngine was followed from here:

<https://cloud.google.com/python/django/appengine>

#### Secrets

The sample for creating the secrets is located in env/sample.env

