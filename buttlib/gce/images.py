"""gce image functions"""


class GCEImages:
    def getFromFamily(client, project="coreos-cloud", family="coreos-stable"):
        images = client.connection.images().getFromFamily(project=project, family=family).execute()
        return images
