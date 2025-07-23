import datetime
import json
import logging
from application.app import app
import os
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from models.ebook_image import EbookImage

@app.function_name("save_image")
@app.activity_trigger(input_name="input")
def save_image(input: dict) -> str:
    """
    Persists the image with the provided ebook ID and image data.

    Args:
        input (dict): The input dictionary containing ebook ID and image data.

    Returns:
        TODO: TBD
    """
    book_id = input.get("book_id")
    image_data: EbookImage = EbookImage(**input.get("image_data"))

    if not image_data.book_id or not image_data or not image_data.image_id:
        raise ValueError("Missing required fields: 'book_id' or 'image_id (image_file_name)'")

    logging.info(f"Save Image Activity - Starting save for image...")

    # Connect to Azure Table Storage
    table_name = os.getenv("IMAGE_TABLE_CONTAINER_NAME", "images")
    storage_account_name = os.getenv("SOURCE_STORAGE_ACCOUNT_NAME")

    account_url = f"https://{storage_account_name}.table.core.windows.net"
    credential = DefaultAzureCredential()
    table_service = TableServiceClient(endpoint=account_url, credential=credential)
    table_client = table_service.get_table_client(table_name)

    entity = image_data.model_dump(by_alias=True)
    entity["extracted_image_data"] = json.dumps(entity["extracted_image_data"], default=str)  # Serialize nested data

    logging.info(f"Upserting entity: {json.dumps(entity, indent=2, default=str)}")
    table_client.upsert_entity(entity)

    logging.info(f"Save Image Activity - Finished saving image: {image_data.image_id} for ebook: {image_data.book_id}")
    return image_data.image_id  # Return the image file name as the identifier for the saved image


# def serialyze_image_data(partition_key: str,
#                          row_key: str, 
#                          image_data: dict) -> dict:
#     """
#     Serializes image data for storage.

#     Args:
#         partition_key (str): The partition key for the image.
#         row_key (str): The row key for the image.
#         image_data (dict): The image data to be serialized.

#     Returns:
#         dict: Serialized image data.
#     """
#     allowed_types = (str, int, float, bool, type(None), datetime)

#     serialized = {
#         "PartitionKey": partition_key,
#         "RowKey": row_key
#     }

#     for key, value in image_data.items():
#         if isinstance(value, allowed_types):
#             serialized[key] = value
#         else:
#             serialized[key] = str(value)  # fallback: stringify unsupported types

#     return serialized