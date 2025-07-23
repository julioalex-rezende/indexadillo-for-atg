import logging
from application.app import app
from models.ebook_image import ExtractedImageData

@app.function_name("refine_description")
@app.activity_trigger(input_name="input")
def refine_description(input: dict) -> str:
    """
    Refines the description of the image

    Args:
        input (dict): The input dictionary containing image data and description.

    Returns:
        (str): The refined description for the image.
    """

    ebook_image: ExtractedImageData = ExtractedImageData(**input.get("image"))
    description: str = input.get("description")

    if not description:
        logging.info(f"Image {ebook_image.image_file_name} does not have a suggested alt text - no need to refine.")
        return None

    logging.info(f"Description Refinement Activity - Starting refinement of description for {ebook_image.image_file_name}...")

    # TODO: Call inference_client logic to refine description
    refined_description = "TBD - from inference_client refinement"

    return refined_description