import pytest
import requests

from mounty import Mountebank
from mounty.models import ImposterResponse, Imposter, Stub, RecordedRequest

MOUNTEBANK_URL = "http://localhost:2525"
IMPOSTER_PORT = 4555
SIMPLE_IMPOSTER = {
    "port": IMPOSTER_PORT,
    "protocol": "http",
    "stubs": [{"responses": [{"is": {"statusCode": 201}}]}],
}


@pytest.fixture
def mountebank():
    mountebank = Mountebank(url=MOUNTEBANK_URL)
    yield mountebank
    mountebank.delete_all_imposters()


class TestRealMountebank:
    def test_add_imposter_json(self, mountebank):
        imposter = mountebank.add_imposter(imposter=SIMPLE_IMPOSTER)
        assert type(imposter) == ImposterResponse
        assert imposter.numberOfRequests == 0

    def test_add_imposter_object_with_predicates_and_recorded_requests(
        self, mountebank
    ):
        imposter = mountebank.add_imposter(
            imposter=Imposter(
                port=4555,
                recordRequests=True,
                protocol="http",
                stubs=[
                    Stub(
                        predicates=[
                            {
                                "and": [
                                    {
                                        "equals": {
                                            "path": "/test",
                                            "method": "POST",
                                            "headers": {
                                                "Content-Type": "application/json"
                                            },
                                        }
                                    },
                                ]
                            }
                        ],
                        responses=[{"is": {"statusCode": 201}}],
                    )
                ],
            )
        )
        assert imposter.numberOfRequests == 0
        requests.post(url="http://localhost:4555/test", json={"nothing": "to see here"})
        requests.post(url="http://localhost:4555/test", json={"nothing": "to see here"})
        recorded_requests = mountebank.wait_for_requests(
            port=4555, count=2, timeout=3.0
        )
        assert len(recorded_requests) == 2
        recorded_request = recorded_requests[0]
        assert type(recorded_request) == RecordedRequest
        assert recorded_request.method == "POST"
        assert recorded_request.path == "/test"
        assert recorded_request.body == {"nothing": "to see here"}
