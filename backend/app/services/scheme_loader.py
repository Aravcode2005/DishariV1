"""Load immutable source configuration once per application lifespan."""
from copy import deepcopy
from pathlib import Path

from pydantic import ValidationError

from app.schemas.schemes import SchemeCatalog

DEFAULT_SCHEMES_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes_wb.json"


class SchemeConfigurationError(Exception):
    pass


class SchemeNotFoundError(Exception):
    pass


class SchemeLoader:
    def __init__(self, path: Path = DEFAULT_SCHEMES_PATH) -> None:
        try:
            catalog = SchemeCatalog.model_validate_json(path.read_bytes(), strict=True)
        except (OSError, ValidationError, ValueError):
            raise SchemeConfigurationError("Scheme configuration is missing or invalid; check app/data/schemes_wb.json") from None
        self._data = catalog.model_dump(mode="json")
        self.version = catalog.ruleset_version
        self._schemes = {scheme["scheme_id"]: scheme for scheme in self._data["schemes"]}

    def schemes(self) -> list[dict]:
        return deepcopy(list(self._schemes.values()))

    def get_scheme(self, scheme_id: str) -> dict:
        if scheme_id not in self._schemes:
            raise SchemeNotFoundError("Scheme not found")
        return deepcopy(self._schemes[scheme_id])

    def checks(self) -> list[dict]:
        return deepcopy(self._data["cross_document_checks"]["checks"])
