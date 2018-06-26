#!/usr/bin/python3

import boto3

AWS_ACCESS_KEY_ID = "ASIAJI5VJQ5OLFYGLJJQ"
AWS_SECRET_ACCESS_KEY = "SFvDUfKKswbn+oFXg4wN8rnUUjoC5aD75vGPNYCu"

s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key= AWS_SECRET_ACCESS_KEY)
bucket_name = 'clusterbuilder'
prefix = ''
response = s3_client.list_objects(Bucket = bucket_name, Prefix = prefix)
print(response)
