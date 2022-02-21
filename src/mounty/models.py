import json
import logging
from dataclasses import dataclass, field, is_dataclass, asdict
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


@dataclass(order=True)
class RecordedRequest:
    method: str
    path: str
    body: Union[dict, str, bytes]
    headers: dict = field(default_factory=list)
    query: dict = field(default_factory=list)
    ip: str = ""
    timestamp: str = ""
    requestFrom: str = ""

    def __post_init__(self) -> None:
        """Transform body to json."""
        try:
            self.body = json.loads(self.body)
        except json.decoder.JSONDecodeError:
            logger.warning(
                "Could not json decode the recorded response body",
                extra={"body": self.body},
            )


@dataclass
class Stub:
    responses: List[dict]
    predicates: List = field(default_factory=list)


@dataclass
class Imposter:
    port: int
    protocol: str
    stubs: List[Union[Stub, dict]]
    recordRequests: bool = False
    name: bool = ""


@dataclass
class ImposterResponse(Imposter):
    numberOfRequests: str = ""
    requests: List[Union[RecordedRequest, dict]] = field(default_factory=list)
    key: str = ""
    cert: str = ""
    mutualAuth: bool = False
    _links: dict = field(default_factory=dict)

    @staticmethod
    def from_dict(dict_val: dict) -> "ImposterResponse":
        """
        Create ImposterResponse object from json
        :param dict_val: json representation of an ImposterResponse
        :return:
        """
        return ImposterResponse(
            port=dict_val["port"],
            protocol=dict_val["protocol"],
            stubs=dict_val["stubs"],
            recordRequests=dict_val.get("recordRequests", False),
            name=dict_val.get("name", ""),
            numberOfRequests=dict_val.get("numberOfRequests", 0),
            requests=[RecordedRequest(**req) for req in dict_val.get("requests", [])],
            key=dict_val.get("key", ""),
            cert=dict_val.get("cert", ""),
            mutualAuth=dict_val.get("mutualAuth", ""),
        )

    def __post_init__(self) -> None:
        """
        Convert json request field to objects
        :return: Instance with requests field converted to class instance
        """
        self.requests = [RecordedRequest(**req) for req in self.requests]


class DataclassJSONEncoder(json.JSONEncoder):
    """
    Custom json encoder for dataclasses
    """

    def default(self, obj) -> dict:
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)


class WithoutEmptyFieldsEncoder(json.JSONEncoder):
    """
    Remove fields with empty string as value
    """

    def default(self, obj) -> Dict[str, Any]:
        return {key: val for key, val in obj.__dict__.items() if val != ""}
