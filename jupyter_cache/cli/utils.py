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


def tabulate_cache_records(records: list, hashkeys=False, path_length=None) -> str:
    """Tabulate cache records.

    :param records: list of ``NbCacheRecord``
    :param hashkeys: include a hashkey column
    :param path_length: truncate URI paths to x components
    """
    import tabulate

    return tabulate.tabulate(
        [
            r.format_dict(hashkey=hashkeys, path_length=path_length)
            for r in sorted(records, key=lambda r: r.accessed, reverse=True)
        ],
        headers="keys",
    )


def tabulate_stage_records(records: list, path_length=None, cache=None) -> str:
    """Tabulate cache records.

    :param records: list of ``NbStageRecord``
    :param path_length: truncate URI paths to x components
    :param cache: If the cache is given,
        we use it to add a column of matched cached pk (if available)
    """
    import tabulate

    rows = []
    for record in sorted(records, key=lambda r: r.created, reverse=True):
        cache_record = None
        if cache is not None:
            cache_record = cache.get_cache_record_of_staged(record.uri)
        rows.append(
            record.format_dict(cache_record=cache_record, path_length=path_length)
        )
    return tabulate.tabulate(rows, headers="keys")
