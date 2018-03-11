#!/bin/bash
#MyApp\/(.*?).zip
echo $CODEBUILD_SOURCE_VERSION
if [[ $CODEBUILD_SOURCE_VERSION =~ MyApp\/(.*).zip ]]; then
  echo ${BASH_REMATCH[1]}``;
  aws s3 sync . s3://rdk-testing-source-bucket/${BASH_REMATCH[1]}/;
fi
