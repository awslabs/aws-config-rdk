# Deploying Rules Across Multiple Regions

The RDK is able to run init/deploy/undeploy across multiple regions with
a `rdk -f <region file> -t <region set>`

If no region group is specified, rdk will deploy to the `default` region
set.

To create a sample starter region group, run `rdk create-region-set` to
specify the filename, add the `-o <region set output file name>` this
will create a region set with the following tests and regions
`"default":["us-east-1","us-west-1","eu-north-1","ap-east-1"],"aws-cn-region-set":["cn-north-1","cn-northwest-1"]`
