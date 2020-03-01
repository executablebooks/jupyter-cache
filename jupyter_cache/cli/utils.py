def shorten_path(file_path, length):
    """Split the path into separate parts,
    select the last 'length' elements and join them again
    """
    from pathlib import Path

    if length is None:
        return Path(file_path)
    return Path(*Path(file_path).parts[-length:])


def get_cache(path):
    # load lazily, to improve CLI speed
    from jupyter_cache.cache.main import JupyterCacheBase

    return JupyterCacheBase(path)
