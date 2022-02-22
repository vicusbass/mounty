import pytest

from mounty import Mountebank
from mounty.errors import MissingEnvironmentVariable


class TestMountebankErrors:
    def test_mountebank_missing_url_env_variable(self):
        with pytest.raises(MissingEnvironmentVariable):
            Mountebank.from_env()
