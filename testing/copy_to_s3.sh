#!/bin/bash

if [[ $CODEBUILD_SOURCE_VERSION =~ "MyApp\/(.*?).zip" ]]; then
  aws s3 sync . s3://rdk-testing-source-bucket/${BASH_REMATCH[1]}/;
else
  echo $CODEBUILD_SOURCE_VERSION;
fi
