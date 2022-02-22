[![codecov](https://codecov.io/gh/vicusbass/mounty/branch/main/graph/badge.svg?token=7Y76GKTW5L)](https://codecov.io/gh/vicusbass/mounty)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/vicusbass/mounty.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/vicusbass/mounty/context:python)
# mounty

A wrapper for Mountebank REST API, can be used for existing instances or for testing in CI/CD ephemeral Mountebank instances.

Who/what is Mountebank? Mountebank is an amazing open-source stub/service virtualisation tool, see more [here](http://www.mbtest.org/).
It can be used as a stub service for any external dependency, it can run as proxy (recording and replaying requests), it can be used for load testing services in isolation (stub external requests, so no latency added)


## Installation

```bash
$ pip install mounty
```

## Usage examples:

Start local Mountebank instance in container:

```shell
docker pull bbyars/mountebank:2.6.0
# start the container exposing port 2525 for imposters administration and ports 4555/4556 for imposters
docker run --rm -p 2525:2525 -p 8080:8080 -p 4555:4555 -p 4556:4556 bbyars/mountebank:2.6.0 mb start
```

```python
import requests
from mounty import Mountebank
from mounty.models import Imposter, Stub, RecordedRequest

# the url must contain the port on which Mountebank is listening
mountebank = Mountebank(url="http://localhost:2525")
# or, if MOUNTEBANK_URL variable is defined:
mountebank_from_env = Mountebank.from_env()

# add imposter as dict
imposter = mountebank.add_imposter(imposter={
 "port": 4555,
 "protocol": "http",
 "stubs": [{"responses": [{"is": {"statusCode": 201}}]}],
})

# add another imposter as Imposter object
other_imposter = mountebank.add_imposter(
 imposter=Imposter(
    port=4556,
    protocol="http",
    recordRequests=True,
    stubs=[Stub(responses=[{"is": {"statusCode": 201}}])],
 )
)

# perform 2 requests
requests.post(url="http://localhost:4556")
requests.post(url="http://localhost:4556")
# wait for maximum 2 seconds for the imposter to contain 2 recorded requests
reqs = mountebank.wait_for_requests(port=4556, count=2, timeout=2)
# validate recorded request
assert type(reqs[0]) == RecordedRequest
```

#### Local development

You will first need to clone the repository using git and place yourself in its directory:

```bash
$ poetry install -vv
$ poetry run pytest tests/
```

To make sure that you don't accidentally commit code that does not follow the coding style:

```bash
$ poetry run pre-commit autoupdate
$ poetry run pre-commit install
$ poetry run pre-commit run --all-files
```
