# Infrastructure for Reality Hack 2024

## Setup

### Local

#### Basic setup

```shell
pip install -r requirements.txt
./manage.py migrate
```

#### Create fake test data

```shell
./manage.py setup_test_data
```

#### Get API schema spec

```shell
./manage.py spectacular --file schema.yml
```

#### Run tests

```shell
./test
```

##### Show test coverage via CLI

```shell
coverage report --show-missing
```

##### Render test coverage via HTML

```shell
coverage html
```

#### Run server

```shell
./runserver
```

### Cloud

This server and database are deployed using Google Cloud. The guide to deploying with AppEngine was followed from here:
 
<https://marketplace.digitalocean.com/apps/django#getting-started>

#### Run Server

```shell
./rundeploy
```

