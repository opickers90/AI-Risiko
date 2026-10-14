# AI Risiko
A Docker-based Django app created using [Cookiecutter Django](https://github.com/cookiecutter/cookiecutter-django/).

## TODO
* TBD

## Components
* [Django 4.1.7](https://docs.djangoproject.com/en/4.1/)
* [Django REST Framework 3.14.0](https://www.django-rest-framework.org/)
* PostgreSQL 15 + PostGIS 3.3.2

## Settings
Cookiecutter options used:
```
project_name [My Awesome Project]: AI Risiko
project_slug [ai_risiko]:
description [Behold My Awesome Project!]: AI Risiko
author_name [Daniel Roy Greenfeld]: Seno A. K.
domain_name [example.com]:
email [seno-a.-k.@example.com]:
version [0.1.0]: 0.1.0
Select open_source_license:
1 - MIT
2 - BSD
3 - GPLv3
4 - Apache Software License 2.0
5 - Not open source
Choose from 1, 2, 3, 4, 5 [1]: 5
timezone [UTC]: Asia/Jakarta
windows [n]: y
use_pycharm [n]: n
use_docker [n]: y
Select postgresql_version:
1 - 14
2 - 13
3 - 12
4 - 11
5 - 10
Choose from 1, 2, 3, 4, 5 [1]: 1
Select cloud_provider:
1 - AWS
2 - GCP
3 - Azure
4 - None
Choose from 1, 2, 3, 4 [1]: 1
Select mail_service:
1 - Mailgun
2 - Amazon SES
3 - Mailjet
4 - Mandrill
5 - Postmark
6 - Sendgrid
7 - SendinBlue
8 - SparkPost
9 - Other SMTP
Choose from 1, 2, 3, 4, 5, 6, 7, 8, 9 [1]: 2
use_async [n]: n
use_drf [n]: y
Select frontend_pipeline:
1 - None
2 - Django Compressor
3 - Gulp
4 - Webpack
Choose from 1, 2, 3, 4 [1]: 1
use_celery [n]: y
use_mailhog [n]: y
use_sentry [n]: y
use_whitenoise [n]: y
use_heroku [n]: n
Select ci_tool:
1 - None
2 - Travis
3 - Gitlab
4 - Github
Choose from 1, 2, 3, 4 [1]: 4
keep_local_envs_in_vcs [y]: y
debug [n]: n
```

## Quickstart
0. Make sure [Docker and Docker Compose are installed](https://docs.docker.com/engine/install/)!
1. Build and bring up all the containers:
    ```
    cd /path/to/ai-risiko-frontend
    docker compose -f local.yml up -d --build
    docker compose -f local.yml ps -a
    ```
2. Create the Django admin user:
    `docker compose -f local.yml run --rm django python manage.py createsuperuser`
3. Access the services:
    * Django: http://localhost:8001
    * Django admin: http://localhost:8001/admin/ (refer to .envs/.local/.django to set custom DJANGO_ADMIN_URL)
    * API: http://localhost:8001/api/
    * API docs: http://localhost:8001/api/docs/
    * API schema: http://localhost:8001/api/schema/
    * Documentation: http://localhost:9000
    * Mailpit: http://localhost:8025
    * `ai_risiko` PostgreSQL database can be connected from the Docker host at port 6543 (refer to .envs/.local/.postgres for database details)

## Initial Data
Fixtures are provided to populate the database tables with initial data.
```
cd /path/to/ai-risiko-frontend
docker compose -f local.yml up -d
# extract and unzip administrasiwilayah.zip content to /path/to/ai-risiko-frontend/ai_risiko/administrasiwilayah/fixtures
docker compose -f local.yml run --rm django python manage.py loaddata --app airisiko group.json
docker compose -f local.yml run --rm django python manage.py loaddata --app administrasiwilayah pulau.json
docker compose -f local.yml run --rm django python manage.py loaddata --app administrasiwilayah provinsi.json
docker compose -f local.yml run --rm django python manage.py loaddata --app administrasiwilayah kabupaten_kota.json
docker compose -f local.yml run --rm django python manage.py loaddata --app administrasiwilayah kecamatan.json
docker compose -f local.yml run --rm django python manage.py loaddata --app administrasiwilayah desa.json
```

## Useful Commands
* Django shell
    ```
    docker compose -f local.yml run --rm django python manage.py shell
    ```
* Django showmigrations
    ```
    docker compose -f local.yml run --rm django python manage.py showmigrations
    ```
* Django makemigrations
    ```
    docker compose -f local.yml run --rm django python manage.py makemigrations
    ```
* Django migrate
    ```
    docker compose -f local.yml run --rm django python manage.py migrate
    ```
* Run unit tests
    ```
    docker compose -f local.yml run --rm django pytest
    docker compose -f local.yml run --rm django python manage.py test
    ```
* Show all container logs
    ```
    docker compose -f local.yml logs -f
    ```
* Show Django container logs
    ```
    docker compose -f local.yml logs django -f
    ```
* Enter shell in Django container
    ```
    docker compose -f local.yml exec -it django bash
    ```
* Connect to the database in Postgres container
    ```
    docker compose -f local.yml exec -it postgres psql -U buCvSEmfSDUtugnUxRrCWsEVAsQmBdJg ai_risiko
    ```

## END AI Risiko README

---

## START Cookiecutter Django README

AI Risiko

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Settings

Moved to [settings](http://cookiecutter-django.readthedocs.io/en/latest/settings.html).

## Basic Commands

### Setting Up Your Users

-   To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

-   To create a **superuser account**, use this command:

        $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    $ mypy ai_risiko

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

#### Running tests with pytest

    $ pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html#sass-compilation-live-reloading).

### Celery

This app comes with Celery.

To run a celery worker:

``` bash
cd ai_risiko
celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important *where* the celery commands are run. If you are in the same folder with *manage.py*, you should be right.

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. For that reason local SMTP server [MailHog](https://github.com/mailhog/MailHog) with a web interface is available as docker container.

Container mailhog will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html) for more details how to start all containers.

With MailHog running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html).
