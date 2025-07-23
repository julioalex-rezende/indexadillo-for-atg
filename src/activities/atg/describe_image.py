import logging
from application.app import app
from models.ebook_image import ExtractedImageData, ImagePurposeType

@app.function_name("describe_image")
@app.activity_trigger(input_name="input")
def describe_image(input: dict) -> str:
    """
    Describes the images in the ebook based on the provided input.

    Args:
        input: (dict): The input dictionary containing image and purpose information.

    Returns:
        (str): The suggested alt text for the image.
    """
    ebook_image: ExtractedImageData = ExtractedImageData(**input.get("image"))
    image_purpose: ImagePurposeType = ImagePurposeType(input.get("image_purpose"))

    if ebook_image.roles_applied == "presentation" or image_purpose == ImagePurposeType.PRESENTATION:
        logging.info(f"Image {ebook_image.image_file_name} is a Presentational Image - no need to describe.")
        return None
    
    if ebook_image.existing_alt_text:
        logging.info(f"Image {ebook_image.image_file_name} already has an existing alt text - no need to describe.")
        return None

    logging.info(f"Describe Image Activity - Starting description of image {ebook_image.image_file_name}...")

    # TODO: Call inference_client logic to generate alt text
    suggested_alt_text = "TBD - from inference_client"
    
    return suggested_alt_text