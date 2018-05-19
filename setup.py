#    Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#
#        http://aws.amazon.com/apache2.0/
#
#    or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='rdk',
      version='0.3.13',
      description='Rule Development Kit CLI for AWS Config',
      long_description=readme(),
      url='https://github.com/awslabs/aws-config-rdk/',
      author='Michael Borchert',
      author_email='mborch@amazon.com',
      license='Apache License Version 2.0',
      packages=['rdk'],
      install_requires=[
          'boto3',
          'mock',
      ],
      scripts=['bin/rdk'],
      zip_safe=False,
      include_package_data=True)
