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

#### With poetry
```shell
POETRY_DOTENV_LOCATION=.env.local poetry shell
poetry install
./manage.py migrate
```

#### Run local docker against local django
`docker compose -f docker-compose.dev.yml up`


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

## Containerization

### Local Image

#### Build the Image (Required)

```shell
./build-image.sh
```

#### Run the Image (Optional)

```shell
./run-container.sh
```

### Docker Compose

#### Run

```shell
docker compose up
```

#### Destroy Volume (Optional)

```shell
docker compose down -v
```
