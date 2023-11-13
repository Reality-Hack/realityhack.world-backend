[![status-badge](https://ci.codeberg.org/api/badges/12758/status.svg)](https://ci.codeberg.org/repos/12758)

# Infrastructure for Reality Hack 2024

## Setup

Set up `.env` file (local and cloud):

```shell
cp .env.example .env
```

Modify the contents of the `.env` file to match KeyCloak configuration information.

### Local

#### Basic setup

```shell
sudo apt-get install libpq-dev
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


#### Setup

If `docker` is not installed, run:

```shell
snap install docker
```

This server and database are deployed using Google Cloud. The guide to deploying with AppEngine was followed from here:
 
<https://marketplace.digitalocean.com/apps/django#getting-started>

#### Run Server

```shell
./rundeploy
```

## Keycloak / OpenIDConnect

Codeberg (Forgejo/Gitea) is used as the primary identity provider. Documentation on using Codeberg with Keycloak:

<https://docs.codeberg.org/integrations/keycloak/>
