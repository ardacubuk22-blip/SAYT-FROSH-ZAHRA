from .kultursanat import KultursanatAdapter

ADAPTERS = {
    "kultursanat": KultursanatAdapter,
}


def get_adapter(source):
    try:
        return ADAPTERS[source.adapter](source)
    except KeyError:
        raise LookupError(f"No adapter named '{source.adapter}'") from None
