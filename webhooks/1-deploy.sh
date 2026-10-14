#!/usr/bin/env bash

cd $WORKING_DIR

# send email notifications
MAIL_SUBJECT_START="[AI Risiko] [BACKEND TASK] Started GitHub webhook deploy.sh"

MAIL_CONTENT_START="The GitHub webhook deploy.sh has started."

if [ -v NOTIFY_EMAIL_ADDRESS ]; then
    echo "$MAIL_CONTENT_START" | mail -s "$MAIL_SUBJECT_START" $NOTIFY_EMAIL_ADDRESS
fi

if [ -v NOTIFY_EMAIL_ADDRESS_2 ]; then
    echo "$MAIL_CONTENT_START" | mail -s "$MAIL_SUBJECT_START" $NOTIFY_EMAIL_ADDRESS_2
fi

FAILED_STEPS=""

# pull latest code
if ! git -c credential.helper='!f() { sleep 1; echo "username=${GIT_USER}"; echo "password=${GIT_PASSWORD}"; }; f' pull; then
    FAILED_STEPS="${FAILED_STEPS}git pull, "
fi

# build the containers
if ! docker compose -f production.yml up --detach --build --force-recreate django celeryworker oqceleryworker lowceleryworker celerybeat flower; then
    FAILED_STEPS="${FAILED_STEPS}docker compose up --build, "
fi

# run any migrations
if ! docker compose -f production.yml run --rm django python manage.py migrate; then
    FAILED_STEPS="${FAILED_STEPS}python manage.py migrate, "
fi

# prune image and builder cache
docker image prune -f

docker builder prune -f

# send a single error email listing any failed steps
if [ -n "$FAILED_STEPS" ]; then
    MAIL_SUBJECT_ERROR="[AI Risiko] [BACKEND TASK] Error during GitHub webhook deploy.sh"

    MAIL_CONTENT_ERROR="The following step(s) of the GitHub webhook deploy.sh FAILED: ${FAILED_STEPS%, }"

    if [ -v NOTIFY_EMAIL_ADDRESS ]; then
        echo "$MAIL_CONTENT_ERROR" | mail -s "$MAIL_SUBJECT_ERROR" $NOTIFY_EMAIL_ADDRESS
    fi

    if [ -v NOTIFY_EMAIL_ADDRESS_2 ]; then
        echo "$MAIL_CONTENT_ERROR" | mail -s "$MAIL_SUBJECT_ERROR" $NOTIFY_EMAIL_ADDRESS_2
    fi

    exit 1
fi

# send email notifications
MAIL_SUBJECT_COMPLETE="[AI Risiko] [BACKEND TASK] Completed GitHub webhook deploy.sh"

MAIL_CONTENT_COMPLETE="The GitHub webhook deploy.sh has completed without errors."

if [ -v NOTIFY_EMAIL_ADDRESS ]; then
    echo "$MAIL_CONTENT_COMPLETE" | mail -s "$MAIL_SUBJECT_COMPLETE" $NOTIFY_EMAIL_ADDRESS
fi

if [ -v NOTIFY_EMAIL_ADDRESS_2 ]; then
    echo "$MAIL_CONTENT_COMPLETE" | mail -s "$MAIL_SUBJECT_COMPLETE" $NOTIFY_EMAIL_ADDRESS_2
fi
