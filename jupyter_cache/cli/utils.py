from pathlib import Path


def shorten_path(file_path, length):
    """Split the path into separate parts,
    select the last 'length' elements and join them again
    """
    if length is None:
        return Path(file_path)
    return Path(*Path(file_path).parts[-length:])
