# The samples here are assuming you already started Mountebank in local environment using docker or node library
# and the ports used for imposters are exposed (4555 and 4556 in these samples)
# But it will also work great with any Mountebank setup
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

# mountebank admin
mountebank = Mountebank(url=MOUNTEBANK_URL)
# or, if you defined MOUNTEBANK_URL environment variable
mountebank_from_env = Mountebank.from_env()

# add an imposter using a Python dict
imposter = mountebank.add_imposter(imposter=SIMPLE_IMPOSTER)
assert type(imposter) == ImposterResponse
response = requests.post(url="http://localhost:4555/test")
assert response.status_code == 201

# add an imposted using Imposter object, with record_requests enabled, on another port
imposter = mountebank.add_imposter(
    imposter=Imposter(
        port=4556,
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
                                    "headers": {"Content-Type": "application/json"},
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

# POST 2 times to the imposter URL, using the predicate path
requests.post(url="http://localhost:4556/test", json={"nothing": "to see here"})
requests.post(url="http://localhost:4556/test", json={"nothing": "to see here"})
# wait for both responses
recorded_requests = mountebank.wait_for_requests(port=4556, count=2, timeout=3.0)

assert len(recorded_requests) == 2
recorded_request = recorded_requests[0]
assert type(recorded_request) == RecordedRequest
assert recorded_request.method == "POST"
assert recorded_request.path == "/test"
assert recorded_request.body == {"nothing": "to see here"}

# get the imposter on port 4555
_imposter = mountebank.get_imposter(4555)
assert type(_imposter) == ImposterResponse

# get all imposters
_imposters = mountebank.get_imposters()

# overwrite stubs on imposter
mountebank.overwrite_stubs_on_imposter(
    [
        Stub(
            predicates=[
                {
                    "and": [
                        {
                            "equals": {
                                "path": "/test",
                                "method": "POST",
                                "headers": {"Content-Type": "application/json"},
                            }
                        },
                    ]
                }
            ],
            responses=[{"is": {"statusCode": 200}}],
        )
    ],
    4556,
)

# delete recorded requests from imposter
mountebank.delete_requests_from_imposter(4556)

# delete imposter
mountebank.delete_imposter(4556)

# delete all imposters (very useful in a Pytest fixture)
mountebank.delete_all_imposters()
