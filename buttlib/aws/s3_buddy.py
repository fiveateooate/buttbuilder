import boto3


class S3Buddy():
    def __init__(self, region):
        self.__client = boto3.client('s3', region_name=region)

    def list_bucket(self, name):
        print(name)
        response = self.__client.list_objects(Bucket=name)
        print(response)
