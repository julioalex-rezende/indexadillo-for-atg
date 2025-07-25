import enum
import logging
from azure.durable_functions import DurableOrchestrationContext, RetryOptions
from application.app import app
import os

from models.ebook_object import EbookObject, EbookProcessStatus
from models.ebook_image import EbookImage, ExtractedImageData, ImagePurposeType

@app.function_name(name="atg_dispatch_process")  # The name used by client.start_new("atg_dispatch_process")
@app.orchestration_trigger(context_name="context")
def atg_dispatch_process(context: DurableOrchestrationContext):
    input = context.get_input()
    logging.info(f'Starting alt-text generation...')
    
    container_name = input.get("defaults").get("EPUB_BLOB_CONTAINER_NAME")
    if container_name is None:
        raise ValueError("EPUB_BLOB_CONTAINER_NAME is not set")
    
    blob_amount_parallel = input.get("defaults").get("BLOB_AMOUNT_PARALLEL")
    if blob_amount_parallel is None:
        raise ValueError("BLOB_AMOUNT_PARALLEL is not set")
    
    # For every item in iterable create a sub orchestrator (should be every file in the blob storage)
    continuation_token = None
    array_position = 0
    while True:
        prefix_list = [""] if "prefix_list" not in input else input["prefix_list"] 
        
        # Call the activity to list blobs in chunks
        blob_list_result = yield context.call_activity("list_blobs", {
                    "container_name": container_name,
                    "continuation_token": continuation_token,
                    "chunk_size": blob_amount_parallel,
                    "prefix_list_offset": array_position,
                    "prefix_list": prefix_list
            })
        
        if(len(blob_list_result["blob_names"]) == 0):
            break
        
        continuation_token = blob_list_result["continuation_token"]
        array_position = blob_list_result["prefix_list_offset"]
        task_list = []
        
        # For each blob name, create a sub-orchestrator task
        for blob_name in blob_list_result["blob_names"]:
            document_retry_options = RetryOptions(first_retry_interval_in_milliseconds=60_000, max_number_of_attempts=3)
            task_list.append(context.call_sub_orchestrator_with_retry(
                name="atg_process_document",
                retry_options=document_retry_options,
                input_={"blob_url": blob_name}))

        # wait for all tasks to complete
        yield context.task_all(task_list)

@app.function_name(name="atg_process_document") 
@app.orchestration_trigger(context_name="context")
def atg_process_document(context: DurableOrchestrationContext):
    input = context.get_input()
    
    service_retry_options = RetryOptions(first_retry_interval_in_milliseconds=3000, max_number_of_attempts=3)
    
    ebook_url = input["blob_url"]
    
    logging.info(f'Processing ebook at URL: {ebook_url}')
    
    # TODO: Include handling for metadata api call for ebook (id)

    # extract static content (metadata+images) from the ebook
    ebook_object: dict = yield context.call_activity_with_retry("extract_ebook", service_retry_options, ebook_url)

    # save ebook object to table storage (ebook_table) with Pending status
    ebook_id = yield context.call_activity_with_retry(
        "save_ebook", 
        service_retry_options, 
        {"ebook_object": ebook_object, "status": EbookProcessStatus.PENDING.value}
    )

    ebook_object = EbookObject(**ebook_object)

    # Iterate over the ebook images and process each image
    if not ebook_object.images:
        logging.info("No images found in the ebook. Skipping image processing.")
        ebook_id = yield context.call_activity_with_retry(
            "save_ebook", 
            service_retry_options, 
            {"ebook_object": ebook_object.model_dump(), "status": EbookProcessStatus.PROCESSED.value}
        )
        return ebook_id

    status = EbookProcessStatus.PROCESSING
    ebook_id = yield context.call_activity_with_retry(
        "save_ebook", 
        service_retry_options, 
        {"ebook_object": ebook_object.model_dump(), "status": EbookProcessStatus.PROCESSING.value}
    )
    for extracted_image in ebook_object.images: # extract_image_data becomes immutable
        logging.info(f'Processing image: {extracted_image.image_file_name} for ebook: {ebook_object.title}')

        # generate image purpose for each image
        image_purpose: str = yield context.call_activity_with_retry(
            "generate_image_purpose",
            service_retry_options,
            extracted_image.model_dump()
        )

        # describe each image (generate alt text)
        description: str = yield context.call_activity_with_retry(
            "describe_image", 
            service_retry_options, 
            {"image": extracted_image.model_dump(), "image_purpose": image_purpose}
        )

        # refine description (if needed)
        refined_description: str = yield context.call_activity_with_retry(
            "refine_description", 
            service_retry_options, 
            {"image": extracted_image.model_dump(), "description": description}
        )

        image = EbookImage(
            book_id = ebook_id,
            image_id = extracted_image.image_file_name,
            extracted_image_data = extracted_image,
            purpose = image_purpose,
            suggested_alt_text = refined_description
        )

        # save image with alt text to Table Storage
        yield context.call_activity_with_retry(
            "save_image", 
            service_retry_options,
            {"ebook_id": ebook_id, "image_data": image.model_dump()}
        )

    # wait for all image processing tasks to complete
    logging.info(f'Finished processing ebook: {ebook_object.title} by {ebook_object.author}')
    
    # update ebook status to processed in table storage
    status = EbookProcessStatus.PROCESSED
    ebook_id = yield context.call_activity_with_retry("save_ebook", service_retry_options, {"ebook_object": ebook_object.model_dump(), "status": status.value})

    return ebook_id
