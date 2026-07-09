"""Container image reference helpers."""

from awx_docker.utilities.load_configuration import DEFAULT_IMAGE_TAG


def split_image_ref(image_ref: str, default_tag: str = DEFAULT_IMAGE_TAG) -> tuple[str, str]:
    """Split an image ref into name and tag.

    Parameters
    ----------
    image_ref : str
        Container image reference to split.
    default_tag : str
        Tag to use when ``image_ref`` does not include one.

    Returns
    -------
    tuple[str, str]
        Image name and tag.
    """
    if ":" not in image_ref.rsplit("/", 1)[-1]:
        return image_ref, default_tag
    image_name, image_tag = image_ref.rsplit(":", 1)
    return image_name, image_tag
