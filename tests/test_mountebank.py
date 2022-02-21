import json
import httpretty
import pytest

from http import HTTPStatus
from mounty.models import Stub, Imposter, ImposterResponse
from mounty.errors import MissingFields, NotFound
from mounty import Mountebank


MOUNTEBANK_URL = "https://mountebank.ca"
IMPOSTER_PORT = 4555
SIMPLE_IMPOSTER = {
    "port": IMPOSTER_PORT,
    "protocol": "https",
    "stubs": [{"responses": [{"is": {"statusCode": 201}}]}],
}
SIMPLE_IMPOSTER_STUB = SIMPLE_IMPOSTER.copy()
SIMPLE_IMPOSTER_STUB.update(
    {
        "requests": [],
        "numberOfRequests": 0,
        "recordRequests": False,
    }
)


@pytest.fixture
def mock_env_variables(monkeypatch):
    monkeypatch.setenv("MOUNTEBANK_URL", MOUNTEBANK_URL)


@pytest.fixture(scope="session")
def mountebank():
    return Mountebank(url=MOUNTEBANK_URL)


@httpretty.activate
class TestMountebankAdmin:
    def test_mountebank_from_env_variables(self, mock_env_variables):
        mountebank = Mountebank.from_env()
        assert mountebank.url == MOUNTEBANK_URL

    def test_add_imposter_json(self, mountebank):
        httpretty.register_uri(
            httpretty.POST,
            f"{MOUNTEBANK_URL}/imposters",
            status=HTTPStatus.CREATED,
            body=json.dumps(SIMPLE_IMPOSTER_STUB),
        )
        imposter = mountebank.add_imposter(imposter=SIMPLE_IMPOSTER)
        assert type(imposter) == ImposterResponse
        assert imposter.numberOfRequests == 0

    def test_add_imposter_object(self, mountebank):
        httpretty.register_uri(
            httpretty.POST,
            f"{MOUNTEBANK_URL}/imposters",
            status=HTTPStatus.CREATED,
            body=json.dumps(SIMPLE_IMPOSTER_STUB),
        )
        imposter = mountebank.add_imposter(
            imposter=Imposter(
                port=4555,
                protocol="http",
                stubs=[Stub(responses=[{"is": {"statusCode": 201}}])],
            )
        )
        assert type(imposter) == ImposterResponse
        assert imposter.numberOfRequests == 0

    def test_add_imposter_rejected(self, mountebank):
        httpretty.register_uri(
            httpretty.POST,
            f"{MOUNTEBANK_URL}/imposters",
            status=HTTPStatus.BAD_REQUEST,
            body=json.dumps(
                {
                    "errors": [
                        {"code": "bad data", "message": "unrecognized response type"}
                    ]
                }
            ),
        )
        with pytest.raises(MissingFields) as err:
            mountebank.add_imposter(imposter=SIMPLE_IMPOSTER)
        assert err.value.code == "bad data"
        assert err.value.message == "unrecognized response type"

    def test_wait_for_requests(self, mountebank):
        imposter_requests_stub = SIMPLE_IMPOSTER.copy()
        imposter_requests_stub.update(
            {
                "numberOfRequests": 1,
                "recordRequests": True,
                "requests": [
                    {"method": "POST", "path": "/foo", "body": '{"it": "works"}'},
                    {"method": "POST", "path": "/foo", "body": '{"it": "works again"}'},
                ],
            }
        )

        httpretty.register_uri(
            httpretty.GET,
            f"{MOUNTEBANK_URL}/imposters/{IMPOSTER_PORT}",
            status=HTTPStatus.OK,
            responses=[
                httpretty.Response(body=json.dumps(SIMPLE_IMPOSTER_STUB)),
                httpretty.Response(body=json.dumps(imposter_requests_stub)),
            ],
        )

        reqs = mountebank.wait_for_requests(IMPOSTER_PORT, count=2)
        assert len(reqs) == 2
        assert len(httpretty.latest_requests()) == 2
        assert reqs[0].body == {"it": "works"}
        assert reqs[1].body == {"it": "works again"}

    def test_get_imposter(self, mountebank):
        httpretty.register_uri(
            httpretty.GET,
            f"{MOUNTEBANK_URL}/imposters/{IMPOSTER_PORT}",
            status=HTTPStatus.OK,
            body=json.dumps(SIMPLE_IMPOSTER_STUB),
        )
        imposter = mountebank.get_imposter(IMPOSTER_PORT)
        assert type(imposter) == ImposterResponse

    def test_get_imposters(self, mountebank):
        _SIMPLE_IMPOSTER_STUB = SIMPLE_IMPOSTER_STUB.copy()
        _SIMPLE_IMPOSTER_STUB["port"] = 4999
        httpretty.register_uri(
            httpretty.GET,
            f"{MOUNTEBANK_URL}/imposters",
            status=HTTPStatus.OK,
            body=json.dumps([SIMPLE_IMPOSTER_STUB, _SIMPLE_IMPOSTER_STUB]),
        )
        imposters = mountebank.get_imposters()
        assert type(imposters) == list
        assert imposters[0] == ImposterResponse(**SIMPLE_IMPOSTER_STUB)
        assert imposters[1] == ImposterResponse(**_SIMPLE_IMPOSTER_STUB)

    def test_delete_imposter(self, mountebank):
        httpretty.register_uri(
            httpretty.DELETE,
            f"{MOUNTEBANK_URL}/imposters/{IMPOSTER_PORT}",
            status=HTTPStatus.OK,
            body=json.dumps(SIMPLE_IMPOSTER_STUB),
        )
        imposter = mountebank.delete_imposter(IMPOSTER_PORT)
        assert imposter == ImposterResponse(**SIMPLE_IMPOSTER_STUB)

    def test_delete_nonexisting_imposter(self, mountebank):
        httpretty.register_uri(
            httpretty.DELETE,
            f"{MOUNTEBANK_URL}/imposters/{IMPOSTER_PORT}",
            status=HTTPStatus.OK,
            body=json.dumps({}),
        )
        imposter = mountebank.delete_imposter(IMPOSTER_PORT)
        assert imposter is None

    def test_delete_saved_requests(self, mountebank):
        httpretty.register_uri(
            httpretty.DELETE,
            f"{MOUNTEBANK_URL}/imposters/{IMPOSTER_PORT}/savedRequests",
            status=HTTPStatus.OK,
            body=json.dumps(SIMPLE_IMPOSTER_STUB),
        )
        imposter = mountebank.delete_requests_from_imposter(IMPOSTER_PORT)
        assert imposter == ImposterResponse(**SIMPLE_IMPOSTER_STUB)

    def test_delete_saved_requests_non_existing_imposter(self, mountebank):
        httpretty.register_uri(
            httpretty.DELETE,
            f"{MOUNTEBANK_URL}/imposters/{IMPOSTER_PORT}/savedRequests",
            status=HTTPStatus.NOT_FOUND,
            body=json.dumps(
                {
                    "errors": [
                        {
                            "code": "no such resource",
                            "message": "Try POSTing to /imposters first?",
                        }
                    ]
                }
            ),
        )
        with pytest.raises(NotFound) as err:
            mountebank.delete_requests_from_imposter(IMPOSTER_PORT)
        assert err.value.code == "no such resource"
        assert err.value.message == "Try POSTing to /imposters first?"

    def test_delete_imposters(self, mountebank):
        httpretty.register_uri(
            httpretty.DELETE,
            f"{MOUNTEBANK_URL}/imposters",
            status=HTTPStatus.OK,
            body=json.dumps([SIMPLE_IMPOSTER_STUB]),
        )
        imposters = mountebank.delete_all_imposters()
        assert imposters == [ImposterResponse(**SIMPLE_IMPOSTER_STUB)]

    def test_overwrite_imposters_stubs(self, mountebank):
        _updated_imposter = SIMPLE_IMPOSTER_STUB.copy()
        _updated_imposter["stubs"].append({"responses": [{"is": {"statusCode": 200}}]})

        httpretty.register_uri(
            httpretty.PUT,
            f"{MOUNTEBANK_URL}/imposters/{IMPOSTER_PORT}/stubs",
            status=HTTPStatus.OK,
            body=json.dumps(_updated_imposter),
        )
        imposter = mountebank.overwrite_stubs_on_imposter(
            port=IMPOSTER_PORT,
            stubs=[
                Stub(responses=[{"is": {"statusCode": 201}}]),
                {"responses": [{"is": {"statusCode": 200}}]},
            ],
        )
        assert imposter == ImposterResponse(**_updated_imposter)

    def test_overwrite_imposters(self, mountebank):
        httpretty.register_uri(
            httpretty.PUT,
            f"{MOUNTEBANK_URL}/imposters",
            status=HTTPStatus.OK,
            body=json.dumps(
                {"imposters": [SIMPLE_IMPOSTER_STUB, SIMPLE_IMPOSTER_STUB]}
            ),
        )
        imposters = mountebank.overwrite_imposters(
            SIMPLE_IMPOSTER, Imposter(**SIMPLE_IMPOSTER)
        )
        assert imposters == [
            ImposterResponse(**SIMPLE_IMPOSTER_STUB),
            ImposterResponse(**SIMPLE_IMPOSTER_STUB),
        ]
