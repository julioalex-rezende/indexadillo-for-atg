import logging
from application.app import app
import os
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential

from models.ebook_object import EbookObject

@app.function_name("save_ebook")
@app.activity_trigger(input_name="input")
def save_ebook(input: dict) -> str:
    """
    Saves the ebook with the provided alt text.

    Args:
        input (dict): The input dictionary containing ebook information.

    Returns:
        TODO: TBD
    """
    ebook_object = EbookObject(**input.get("ebook_object"))
    status = input.get("status", "pending")

    logging.info(f"Save Ebook Activity - Starting save for ebook...")

    # Connect to Azure Table Storage
    table_name = os.getenv("EBOOK_TABLE_CONTAINER_NAME", "books")
    storage_account_name = os.getenv("SOURCE_STORAGE_ACCOUNT_NAME")

    account_url = f"https://{storage_account_name}.table.core.windows.net"
    credential = DefaultAzureCredential()
    table_service = TableServiceClient(endpoint=account_url, credential=credential)
    table_client = table_service.get_table_client(table_name)

    entity = ebook_object.model_dump(by_alias=True)
    entity["status"] = status 
    entity.pop('images', None)  # Safely remove 'images' from the ebook object

    # Save entity
    table_client.upsert_entity(entity)

    logging.info(f"Save Ebook Activity - Finished saving ebook: {ebook_object.title} by {ebook_object.author} with ISBN: {ebook_object.id}")
    return ebook_object.id  # Return the ISBN as the identifier for the saved ebook
