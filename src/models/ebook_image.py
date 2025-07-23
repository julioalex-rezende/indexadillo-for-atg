
from enum import Enum
from typing import Optional
from pydantic import AliasChoices, BaseModel, Field

class ImagePurposeType(Enum):
    PRESENTATION = "Presentation"
    FUNCTIONAL = "Functional"
    TBD = "To Be Determined"

class ExtractedImageData(BaseModel):
    image_file_name: str
    
    # Image related fields
    thumbnail: Optional[str] = Field(default=None)
    html_filename: Optional[str] = Field(default=None)
    image_id: Optional[str] = Field(default=None)
    section: Optional[str] = Field(default=None)
    page_number: Optional[int] = Field(default=None)
    fig_caption: Optional[str] = Field(default=None)
    roles_applied: Optional[str] = Field(default=None)
    aria_attributes: Optional[str] = Field(default=None)

    # context related fields
    pre_context: Optional[str] = Field(default=None)
    post_context: Optional[str] = Field(default=None)

    # Alt text related fields
    existing_alt_text: Optional[str] = Field(default=None)


class EbookImage(BaseModel):
    book_id: str = Field(
        serialization_alias="PartitionKey",
        validation_alias=AliasChoices("book_id", "PartitionKey"),
    )
    image_id: str = Field(
        serialization_alias="RowKey",
        validation_alias=AliasChoices("image_id", "image_file_name", "RowKey"),
    )
    extracted_image_data: ExtractedImageData
    purpose: str
    suggested_alt_text: Optional[str] = Field(default=None)