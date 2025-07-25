import io
import json
import tempfile
import zipfile
import os
import xml.etree.ElementTree as ET
import requests
import logging
from models.ebook_object import EbookObject
from models.ebook_image import ExtractedImageData
from azure.storage.blob import BlobClient
from azure.identity import DefaultAzureCredential
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,                # Set the logging level to INFO
    format='%(asctime)s %(levelname)s %(message)s',  # Optional: format the output
)

def extract_ebook_from_url(ebookurl: str) -> EbookObject:
    """
    Extracts an ebook from a given .epub URL in Azure Blob Storage.
    Downloads, unpacks, reads the .opf file, and extracts all images.

    Args:
        ebookurl (str): The URL of the .epub file in blob storage.

    Returns:
        EbookObject: An object containing metadata and images from the ebook.
    """
    logging.info(f"Starting extraction for ebook: {ebookurl}")

    # Download the epub file from Azure Blob Storage using Azure SDK
    blob_client = BlobClient.from_blob_url(ebookurl, credential=DefaultAzureCredential())
    downloader = blob_client.download_blob()
    epub_bytes = downloader.readall()

    with zipfile.ZipFile(io.BytesIO(epub_bytes), 'r') as zip_file:
        # Find the .opf file in the epub archive
        # This is necessary to extract Book and Images information
        opf_file = find_opf_file(zip_file)

        # Extract Ebook information
        # Responsible for extracting metadata from opf file like title, author, and also images present in the ebook
        ebook_object: EbookObject = get_ebook_info(zip_file, opf_file)

    # logging.info(f"Ebook extracted:\n\t{json.dumps(ebook_object, indent=2, default=lambda o: o.__dict__)}")
    logging.info(f"Finished extraction for ebook: {ebook_object.title} by {ebook_object.author}")

    return ebook_object

def get_ebook_info(zip_file, opf_file) -> EbookObject:
    """
    Extracts information from the .opf file in the epub archive.

    Args:
        zip_file (zipfile.ZipFile): The opened epub file.
        opf_file (str): The name of the .opf file.

    Returns:
        EbookObject: An object containing metadata from the ebook.
    """
    logging.info(f"Extracting Ebook Information from OPF file: {opf_file}")

    opf_content = zip_file.read(opf_file)
    opf_tree = ET.fromstring(opf_content)

    # Extract metadata fields
    isbn_elem = opf_tree.find(".//{*}identifier")
    if isbn_elem is None or not isbn_elem.text:
        raise ValueError("ISBN (identifier) not found in OPF metadata.")
    isbn = isbn_elem.text

    title = opf_tree.find(".//{*}title").text if opf_tree.find(".//{*}title") is not None else "Unknown Title"
    author = opf_tree.find(".//{*}creator").text if opf_tree.find(".//{*}creator") is not None else "Unknown Author"
    
    # Extract Images information
    extracted_images: list[ExtractedImageData] = get_images_info(zip_file, opf_file)

    return EbookObject(
        id=isbn,
        title=title,
        author=author,
        images=extracted_images
    )

def get_images_info(zip_file, opf_file) -> list[ExtractedImageData]:
    """
    Extracts image information from the opf file.
    Traverses xhtml files in the epub archive finding embedded images.

    Args:
        zip_file (zipfile.ZipFile): The opened epub file.
        opf_file (str): The name of the .opf file.

    Returns:
        list[ExtractedImageData]: A list of ExtractedImageData objects containing image data.
    """
    logging.info(f"Extracting Images Information from OPF file: {opf_file}")

    # Get all xhtml file paths from the .opf file
    xhtml_files = get_xhtml_filepaths_from_opf(zip_file, opf_file)
    
    # Gather image data from each xhtml file
    all_image_data = []
    for xhtml_file in xhtml_files:
        all_image_data.extend(gather_file_image_data(zip_file, xhtml_file))

    logging.info(f"Extracted {len(all_image_data)} images from XHTML files.")
    return all_image_data

def find_opf_file(zip_file: zipfile.ZipFile) -> str:
    """
    Finds the .opf file in the epub archive.

    Args:
        zip_file (zipfile.ZipFile): The opened epub file.

    Returns:
        str: The name of the .opf file.
    """
    logging.info("Searching for .opf file in the epub archive.")
    for file_name in zip_file.namelist():
        if file_name.endswith('.opf'):
            return file_name
    
    logging.error("No .opf file found in the epub archive.")
    raise FileNotFoundError("No .opf file found in the epub archive.")

def get_xhtml_filepaths_from_opf(zip_file, opf_file):
    logging.info(f"Reading XHTML files from OPF file: {opf_file}")

    opf_content = zip_file.read(opf_file)
    opf_tree = ET.fromstring(opf_content)

    # ns = {"opf": "http://www.idpf.org/2007/opf"}
    # Find all <item> elements with media-type xhtml/html
    xhtml_files = []
    for item in opf_tree.findall(".//{*}item"):
        media_type = item.attrib.get("media-type", "")
        if "xhtml" in media_type or "html" in media_type:
            href = item.attrib.get("href")
            if href:
                xhtml_files.append(os.path.join(os.path.dirname(opf_file), href))

    logging.info(f"Found {len(xhtml_files)} XHTML files in OPF.")
    return xhtml_files

def get_img_figcaption(img_tag):
    """
    Given a BeautifulSoup <img> tag, return the text of the closest <figcaption>
    within its ancestor <figure>. Returns '' if not found.
    """
    figure = img_tag.find_parent("figure")
    if figure:
        figcaption = figure.find("figcaption")
        if figcaption:
            return figcaption.get_text(strip=True)
    return ""

def gather_file_image_data(zip_file, xhtml_filename) -> list[ExtractedImageData]:
    xhtml_content = zip_file.read(xhtml_filename)
    soup = BeautifulSoup(xhtml_content, "html.parser")

    # Find all <img> elements in the XHTML file
    file_images_list = soup.find_all("img")

    logging.info(f"Reading data from {len(file_images_list)} img elements in {xhtml_filename}.")

    # Generate a list of dictionaries with image data
    # Each dictionary corresponds to an image and contains its attributes
    image_data_dict_list: list[ExtractedImageData] = []
    for an_image in file_images_list:
        # Create an ExtractedImageData object for each image
        image_file_name = os.path.basename(an_image.get("src", ""))
        extracted_image = ExtractedImageData(image_file_name=image_file_name)

        extracted_image.thumbnail = None                    # TODO: Implement Thumbnail
        extracted_image.html_filename = xhtml_filename
        extracted_image.image_id = an_image.get("id", "")
        extracted_image.section = ""                        # TODO: Implement section extraction
        extracted_image.page_number = 0                     # TODO: Implement page number extraction
        extracted_image.fig_caption = get_img_figcaption(an_image)

        # context related fields
        extracted_image.pre_context = None                  # TODO: Implement pre-context extraction
        extracted_image.post_context = None                 # TODO: Implement post-context extraction

        attribute_declarations = ""
        for attr, val in an_image.attrs.items():
            if attr.lower() == "alt":
                # If the image has an alt attribute, set it as existing_alt_text
                extracted_image.existing_alt_text = val
            elif attr.lower() == "role":
                # If the image has a role attribute, set it (e.g., "presentation")
                extracted_image.roles_applied = val
            elif attr.lower() == "title":
                extracted_image.image_title = val
                attribute_declarations += f'{attr}="{val}"\n'
            elif attr.lower() == "aria-labelledby":
                extracted_image.aria_labelled_by = val
                attribute_declarations += f'{attr}="{val}"\n'
            # Grab other accessibilty-related attributes that may be applied.
            elif attr.lower() not in (
                "src",
                "id",
                "class",
                "epub:type",
                "style",
                "width",
                "height",
            ):
                attribute_declarations += f'{attr}="{val}"\n'
        extracted_image.aria_attributes = attribute_declarations.strip()

        # Append the ExtractedImageData object to the list
        image_data_dict_list.append(extracted_image)

    return image_data_dict_list
