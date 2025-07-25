import json
import logging
import os

import azure.functions as func
from azure.durable_functions import DurableOrchestrationClient
from application.app import app

from document_processor.orchestrators.atg_ebook_processor import atg_dispatch_process

from document_processor.activities.listblob import list_blobs
from document_processor.activities.extract_ebook import extract_ebook
from document_processor.activities.generate_image_purpose import generate_image_purpose
from document_processor.activities.describe_image import describe_image
from document_processor.activities.refine_description import refine_description
from document_processor.activities.save_ebook import save_ebook
from document_processor.activities.save_image import save_image

defaults = {
    "BLOB_AMOUNT_PARALLEL": int(os.environ.get("BLOB_AMOUNT_PARALLEL", "20")),
    "EPUB_BLOB_CONTAINER_NAME": os.environ.get("EPUB_BLOB_CONTAINER_NAME", "epub"),
    "EBOOK_TABLE_CONTAINER_NAME": os.environ.get("EBOOK_TABLE_CONTAINER_NAME", "books"),
    "IMAGE_TABLE_CONTAINER_NAME": os.environ.get("IMAGE_TABLE_CONTAINER_NAME", "images")
}

### -----------
# HTTP Trigger
### -----------
@app.function_name(name='atg_process_http')
@app.route(route="atg_process", methods=[func.HttpMethod.POST])
@app.durable_client_input(client_name="client")
async def atg_process_http(req: func.HttpRequest, client: DurableOrchestrationClient) -> func.HttpResponse:
    logging.info('Kick off alt-text-generation process.')
    input = req.get_json()
    instance_id = await client.start_new(
        orchestration_function_name="atg_dispatch_process",
        client_input={"prefix_list": input['prefix_list'], "defaults": defaults})
    
    print(f'Started alt-text generation with id: {instance_id}')
    return func.HttpResponse(instance_id, status_code=200)


### -----------
# Event Grid Trigger
### -----------
@app.function_name(name='atg_process_event_grid')
@app.event_grid_trigger(arg_name='event')
@app.durable_client_input(client_name="client")
async def atg_process_event_grid(event: func.EventGridEvent, client: DurableOrchestrationClient):
    if event.get_json()["api"] != "PutBlob":
        logging.info("Event type is not BlobCreated. Skipping execution.")
        return
    
    path_in_container = extract_path(event)
    logging.info(f'Python EventGrid trigger processed a BlobCreated event. Path: {path_in_container}')

    instance_id = await client.start_new("atg_dispatch_process", client_input={"prefix_list": [path_in_container], "defaults": defaults})
    logging.info(f'Started indexing with id: {instance_id}')


@app.function_name(name='status')
@app.route(route="status", methods=[func.HttpMethod.GET])
@app.durable_client_input(client_name="client")
async def status(req: func.HttpRequest, client: DurableOrchestrationClient) -> func.HttpResponse:
    logging.info('Retrieving status of all orchestrations.')
    results = await client.get_status_all()
    return func.HttpResponse(json.dumps([result.to_json() for result in results]), status_code=200)






def extract_path(event: func.EventGridEvent):
    subject = event.subject
    path_in_container = subject.split("/blobs/", 1)[-1]
    return path_in_container






@app.function_name(name='status_id')
@app.route(route="status/{id}", methods=[func.HttpMethod.GET])
@app.durable_client_input(client_name="client")
async def status_id(req: func.HttpRequest, client: DurableOrchestrationClient) -> func.HttpResponse:
    logging.info('Retrieving status of all orchestrations.')
    id = req.route_params.get('id')
    def str_to_bool(value):
        if value is None:
            return False
        return value.lower() in ['true', '1']
    show_history = str_to_bool(req.params.get('show_history')) or False
    show_history_output = str_to_bool(req.params.get('show_history_output')) or False
    show_input = str_to_bool(req.params.get('show_input')) or False
    result = await client.get_status(instance_id=id, show_history=show_history, show_history_output=show_history_output, show_input=show_input)
    result_json = result.to_json()
    if show_history and hasattr(result, 'historyEvents'):
        result_json["historyEvents"] = list(result.historyEvents)
    else:
        result_json["historyEvents"] = None

    return func.HttpResponse(json.dumps(result_json), status_code=200)

