import logging
from document_processor.ebook_extractor import extract_ebook_from_url
from application.app import app
from models.ebook_object import EbookObject

@app.function_name("extract_ebook")
@app.activity_trigger(input_name="ebookurl")
def extract_ebook(ebookurl: str) -> dict:
    """
    Extracts an ebook based on the provided input and defaults.
    
    Args:
        ebookurl (str): The URL of the ebook to be extracted.

    Returns:
        ebook_object: EbookObject containing the extracted information.
    """
    log_prefix = "Extract Ebook Activity"
    
    logging.info(f"{log_prefix} - Starting extraction for ebook: {ebookurl}")    

    # Extract static image information from the ebook
    ebook_object: EbookObject = extract_ebook_from_url(ebookurl)

    # Extract previous and post content for each image of the ebook
    # TODO: Implement logic to extract previous and post content for each image
    # Integrate with MVE Code
    for image in ebook_object.images:
        # Collect content from images
        image.pre_context = "TBD - Previous content before the image"
        image.post_context = "TBD - Content after the image"
        
        # TODO: investigate whether we yield each image or just complete the list

    logging.info(f"{log_prefix} - Finished extraction for ebook: {ebook_object.title} by {ebook_object.author}")    
    return ebook_object.model_dump()  # Return the ebook object as a dictionary