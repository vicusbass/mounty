import json

from mounty.models import Imposter, Stub, DataclassJSONEncoder


def test_imposter():
    imposter = Imposter(
        port=4555,
        protocol="https",
        stubs=[Stub(responses=[{"is": {"statusCode": 400}}])],
    )
    assert (
        json.dumps(imposter, cls=DataclassJSONEncoder)
        == '{"port": 4555, "protocol": "https", "stubs": [{"responses": [{"is": '
        '{"statusCode": 400}}], "predicates": []}], "recordRequests": false, "name": ""}'
    )


def test_imposter_with_json_stubs():
    imposter = Imposter(
        port=4555,
        protocol="https",
        stubs=[{"responses": [{"is": {"statusCode": 400}}]}],
    )
    assert (
        json.dumps(imposter, cls=DataclassJSONEncoder)
        == '{"port": 4555, "protocol": "https", "stubs": [{"responses": [{"is": '
        '{"statusCode": 400}}]}], "recordRequests": false, "name": ""}'
    )
