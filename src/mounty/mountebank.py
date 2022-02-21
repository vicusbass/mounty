import json
import logging
import os
import time
from dataclasses import asdict
from typing import Any, List, Optional, Union
from requests import HTTPError, Response, Session

from mounty.errors import (
    Conflict,
    ImposterError,
    MissingFields,
    NotFound,
    Unavailable,
    MissingEnvironmentVariable,
)
from mounty.models import (
    Imposter,
    ImposterResponse,
    RecordedRequest,
    Stub,
    WithoutEmptyFieldsEncoder,
)


logger = logging.getLogger(__name__)


class Mountebank:
    """
    An admin client for Mountebank.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._imposters_url = f"{self.url}/imposters"
        self._session = Session()
        self._session.hooks["response"].extend(
            [
                lambda response, *args, **kwargs: response.raise_for_status(),
                lambda response, *args, **kwargs: logger.debug(
                    f"Got response {response.text} from {response.url}"
                ),
            ]
        )

    def __request(
        self, method: str, url: str, *args: Any, **kwargs: Any
    ) -> Optional[Response]:
        """
        A wrapper over requests... request method, with error handling
        :param method: "GET", "POST", etc.
        :param url: request destination
        :return:
        """
        try:
            return self._session.request(method=method, url=url, *args, **kwargs)
        except HTTPError as e:
            self.__handle_exception(e)

            logger.exception("Unexpected error")
            raise Unavailable() from e

    @staticmethod
    def __handle_exception(e):
        if e.response.status_code in [400, 404]:
            try:
                body = e.response.json()
                error = body["errors"][0]
                code = error["code"]
                message = error["message"]

                if code == "resource conflict":
                    raise Conflict(code, message) from e
                if code == "bad data":
                    raise MissingFields(code, message) from e
                if code == "no such resource":
                    raise NotFound(code, message) from e
                else:
                    raise ImposterError(code, message) from e
            except ValueError:
                raise Unavailable() from e

    @classmethod
    def from_env(cls) -> "Mountebank":
        """
        Creates Mountebank admin instance based on MOUNTEBANK_URL env variable
        :return: Mountebank admin instance
        """
        try:
            return cls(url=os.environ["MOUNTEBANK_URL"])
        except KeyError:
            raise MissingEnvironmentVariable(
                "MOUNTEBANK_URL environment variable is missing"
            )

    def add_imposter(self, imposter: Union[dict, Imposter]) -> ImposterResponse:
        """
        Add imposter
        :param imposter:
        :return: ImposterResponse object (Imposter with extra fields)
        """
        if isinstance(imposter, Imposter):
            imposter = asdict(imposter)

        response = self.__request(method="POST", url=self._imposters_url, json=imposter)
        return ImposterResponse(**response.json())

    def delete_imposter(self, port: int) -> ImposterResponse:
        """
        Delete an imposter
        :param port: port
        :return:
        """
        response = self.__request(method="DELETE", url=f"{self._imposters_url}/{port}")
        payload = response.json()
        return ImposterResponse(**payload) if payload else None

    def delete_all_imposters(self) -> [ImposterResponse]:
        """
        Delete all existing imposters
        :return: list of existing imposters before deletion
        """
        response = self.__request(method="DELETE", url=self._imposters_url)
        return [ImposterResponse(**ires) for ires in response.json()]

    def get_imposter(self, port) -> ImposterResponse:
        """
        Retrieve existing imposter details
        :param port: imposter port
        :return:
        """
        response = self.__request(method="GET", url=f"{self._imposters_url}/{port}")
        return ImposterResponse(**response.json())

    def get_imposters(self) -> List[ImposterResponse]:
        """
        Retrieve all existing imposters
        :return:
        """
        response = self.__request(method="GET", url=self._imposters_url)
        return [ImposterResponse(**ires) for ires in response.json()]

    def overwrite_imposters(
        self, *imposters: Union[Imposter, dict]
    ) -> List[ImposterResponse]:
        """
        Overwrite all existing imposters
        :param imposters: new imposters
        :return: Updated list of imposters
        """
        imposters = [
            json.dumps(imposter, cls=WithoutEmptyFieldsEncoder)
            for imposter in imposters
        ]
        response = self.__request(
            method="PUT",
            url=self._imposters_url,
            json={"imposters": imposters},
        )
        return [
            ImposterResponse(**imposter) for imposter in response.json()["imposters"]
        ]

    def overwrite_stubs_on_imposter(
        self, stubs: List[Union[Stub, dict]], port: int
    ) -> ImposterResponse:
        """
        Overwrites stubs in an existing imposter
        :param stubs: List of stubs as dictionary or Stub
        :param port: imposter port
        :return: updated imposter
        """
        stubs = [json.dumps(stub, cls=WithoutEmptyFieldsEncoder) for stub in stubs]
        response = self.__request(
            method="PUT",
            url=f"{self._imposters_url}/{port}/stubs",
            json={"stubs": stubs},
        )
        return ImposterResponse(**response.json())

    def delete_requests_from_imposter(self, port: int) -> Optional[ImposterResponse]:
        """
        Delete all saved requests from an imposter
        :param port: imposter port
        :return: The imposter after deleting the saved requests
        """
        response = self.__request(
            method="DELETE", url=f"{self._imposters_url}/{port}/savedRequests"
        )
        return ImposterResponse(**response.json())

    def wait_for_requests(
        self, port: int, count: int = 1, timeout: float = 5.0
    ) -> List[RecordedRequest]:
        """
        Poll an imposter until a specific number of recorded requests are available
        :param port: imposter port
        :param count: expected number of recorded requests
        :param timeout: timeout
        :return:
        """
        start_time = time.perf_counter()
        while True:
            reqs = self.get_imposter(port).requests
            if len(reqs) >= count:
                return reqs
            else:
                time.sleep(0.5)
                if time.perf_counter() - start_time >= timeout:
                    raise TimeoutError(f"Waited too long for {count} requests on stub.")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} url={self.url}>"
