#!/bin/bash

source .env
AWS_PROFILE=community

Parameters=(
        ParameterKey=botToken,ParameterValue=${BOT_TOKEN}
)

sam build -t ./template.yaml --parameter-overrides "${Parameters[@]}"
sam deploy --profile $AWS_PROFILE --no-confirm-changeset --parameter-overrides "${Parameters[@]}"
