# Infrastructure for Reality Hack 2024

## Setup

### Django

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

#### Run server

```shell
python manage.py runserver
```
