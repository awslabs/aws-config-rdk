# Using RDK to Generate a Lambda Layer in a region (Python3)

By default `rdk init --generate-lambda-layer` will generate an rdklib
lambda layer while running init in whatever region it is run, to force
re-generation of the layer, run `rdk init --generate-lambda-layer` again
over a region

To use this generated lambda layer, add the flag
`--generated-lambda-layer` when running `rdk deploy`. For example:
`rdk -f regions.yaml deploy LP3_TestRule_P39_lib --generated-lambda-layer`

If you created layer with a custom name (by running
`rdk init --custom-lambda-layer`, add a similar `custom-lambda-layer`
flag when running deploy.
