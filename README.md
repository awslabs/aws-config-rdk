

# Steps to setup your local environment 
make freeze
make init

# Editorable mode by activate pipenv
pipenv shell

# Navigagte to rules dir in integration test
cd tests/rdk-cdk-int-rules-dir

# Run RDK command for testing
rdk test
rdk deploy
rdk destroy