from datetime import datetime, timezone
from typing import Optional

from piccolo.columns import (
    Integer,
    Timestamptz,
    Varchar,
)
from piccolo.table import Table

from calliope.models import ImageFormat, ImageModel
from calliope.utils.file import FileMetadata


class Image(Table):
    """
    The high-level attributes of an image.
    """

    # The primary key, a CUID.
    # id = Varchar(length=50, primary_key=True)

    width = Integer()
    height = Integer()
    format = Varchar(length=50)
    url = Varchar()

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    def __str__(self) -> str:
        return f"<Image {self.width}x{self.height}, {self.format}, {self.url}>"

    def __repr__(self) -> str:
        return (
            f"<Image {self.id}: "  # type: ignore[attr-defined]
            f"{self.width}x{self.height}, "
            f"{self.format}, {self.url}"
        )

    @property
    def display_url(self) -> str:
        """
        Returns the URL for displaying this image.
        In cloud environments, returns CDN URL; locally returns local path with leading slash.
        """
        from calliope.utils.google import (
            is_google_cloud_run_environment,
            local_path_to_gcs_url,
        )

        if is_google_cloud_run_environment():
            return local_path_to_gcs_url(self.url)
        else:
            # Ensure local path has leading slash for proper serving
            return f"/{self.url}" if not self.url.startswith("/") else self.url

    def to_pydantic(self) -> Optional[ImageModel]:
        format = ImageFormat.fromMediaFormat(self.format)
        if not format:
            return None
            # print(f"Image: {self.width=}, {self.height=}, {self.format=}, {self.url=}")
            # raise ValueError(f"Invalid image format: {self.format}")

        # Convert local path to full GCS URL for direct access from client
        from calliope.utils.google import (
            is_google_cloud_run_environment,
            local_path_to_gcs_url,
        )

        if is_google_cloud_run_environment():
            url = local_path_to_gcs_url(self.url)
        else:
            # Ensure local path has leading slash for proper serving
            url = f"/{self.url}" if not self.url.startswith("/") else self.url

        return ImageModel(
            width=self.width,
            height=self.height,
            format=format,
            url=url,
        )

    @classmethod
    async def from_pydantic(
        cls, model: ImageModel, file_metadata: FileMetadata
    ) -> "Image":
        width = model.width
        height = model.height
        format = model.format.value
        url = model.url

        date_created = file_metadata.date_created or datetime.now(timezone.utc)
        date_updated = file_metadata.date_updated or date_created

        instance: Optional[Image] = (
            await Image.objects()
            .where(
                Image.url == url,
                Image.format == format,
                Image.width == width,
                Image.height == height,
            )
            .first()
            .run()
        )
        if not instance:
            instance = Image(
                # id=create_cuid(),
                date_created=date_created,
                date_updated=date_updated,
                width=width,
                height=height,
                format=format,
                url=url,
            )

        return instance
