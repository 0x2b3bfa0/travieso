from enum import Enum
from requests.exceptions import JSONDecodeError, HTTPError
from requests.adapters import HTTPAdapter, Retry
from requests_toolbelt.sessions import BaseUrlSession


class TravisHost(str, Enum):
    COM = "api.travis-ci.com"
    ORG = "api.travis-ci.org"


class Travis:
    def __init__(self, host: TravisHost, token: str = "") -> None:
        self.session = BaseUrlSession(base_url=f"https://{host.value}")

        self.session.headers = {"travis-api-version": "3"}
        if token:
            self.session.headers.update({"authorization": f"token {token}"})

        retry = Retry(total=10, backoff_factor=2, status_forcelist=[429, 500])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _request(self, path: str) -> dict:
        response = self.session.get(path)
        response.raise_for_status()
        try:
            return response.json()
        except JSONDecodeError:
            return self._request(path)

    def _paginate(self, path: str) -> iter:
        while True:
            yield (response := self._request(path))

            if response["@pagination"]["is_last"]:
                break
            path = response["@pagination"]["next"]["@href"]

    def repositories(self, organization: str) -> iter:
        for page in self._paginate(f"/owner/{organization}/repos?limit=100"):
            yield from page["repositories"]

    def builds(self, repository: str) -> iter:
        for page in self._paginate(f"/repo/{repository}/builds?limit=100"):
            yield from page["builds"]

    def jobs(self, build: str) -> iter:
        response = self._request(f"/build/{build}/jobs?include=build.request")
        yield from response["jobs"]

    def log(self, job: str) -> str:
        try:
            response = self._request(f"/job/{job}/log")
            return response["content"] or ""
        except HTTPError as exception:
            return str(exception.response.status_code)
