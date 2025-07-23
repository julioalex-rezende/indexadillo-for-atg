import logging
from application.app import app
from models.ebook_image import ExtractedImageData, ImagePurposeType

@app.function_name("generate_image_purpose")
@app.activity_trigger(input_name="image")
def generate_image_purpose(image: dict) -> str:
    """
    Identifies the image purpose based on the provided input.

    Args:
        image (dict): The EbookImage data to describe (as dictionary).

    Returns:
        (str): The inferred image purpose as a string.
    """

    ebook_image: ExtractedImageData = ExtractedImageData(**image)
    if ebook_image.roles_applied == "presentation":
        logging.info(f"Image {ebook_image.image_file_name} is already a Presentational Image - no need to infer.")
        return ImagePurposeType.PRESENTATION.value

    logging.info(f"Generate Image Purpose Activity - Starting generation of Image purpose for {ebook_image.image_file_name}...")

    # TODO: Call inference_client logic to infer image purpose
    # TODO: Decide whether to return ImagePurposeType or a string
    image_purpose: str = ImagePurposeType.TBD.value

    return image_purpose  # Return the inferred image purpose