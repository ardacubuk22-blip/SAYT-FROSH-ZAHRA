from .akm import AkmAdapter
from .kultursanat import KultursanatAdapter
from .sehir_tiyatrolari import SehirTiyatrolariAdapter

ADAPTERS = {
    "kultursanat": KultursanatAdapter,
    "akm": AkmAdapter,
    "sehir_tiyatrolari": SehirTiyatrolariAdapter,
}


def get_adapter(source):
    try:
        return ADAPTERS[source.adapter](source)
    except KeyError:
        raise LookupError(f"No adapter named '{source.adapter}'") from None
