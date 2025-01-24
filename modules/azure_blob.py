from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
from dotenv import load_dotenv

class AzureBlob:
    
    def __init__(self):
        connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        self.container_name = "crawlingdata"
        
        try:
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            self.container_client.create_container()
        except Exception as e:
            print(f"Container already exists!")
            
if __name__ == "__main__":
    load_dotenv()
    AzureBlob()