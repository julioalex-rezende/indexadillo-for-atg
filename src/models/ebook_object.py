from attr import dataclass
from pydantic import AliasChoices, BaseModel, Field
from enum import Enum
from models.ebook_image import ExtractedImageData


class EbookProcessStatus(Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    FAILED = "Failed"

class EbookObject(BaseModel):
    partition_key: str = Field(
        default_factory=lambda: "ebook",
        serialization_alias="PartitionKey",
    )
    id: str = Field(
        serialization_alias="RowKey",
        validation_alias=AliasChoices("isbn","id", "RowKey"),
    )
    
    title: str
    author: str
    images: list[ExtractedImageData] = None  # List of ExtractedImageData objects
