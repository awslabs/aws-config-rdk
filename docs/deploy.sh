#!/bin/bash

zip lambda-deployment.zip ./lambda_function.py
cd ./lib/python3.7/site-packages
zip -r --exclude=*pycache* ../../../lambda-deployment.zip .
cd ../../../

aws lambda update-function-code --function-name FlowLogDataProcessor --zip-file fileb://lambda-deployment.zip --publish
