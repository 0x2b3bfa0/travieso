from json import dump
from pathlib import Path
from typing import Iterator

from joblib import Parallel, delayed
from typer import Argument, Option, Typer

from .travis import Travis, TravisDomain

application = Typer(add_completion=False)


@application.command()
def main(
    owner: str,
    repository: str = Argument(""),
    output: Path = Option(
        ...,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    concurrency: int = 32,
    domain: TravisDomain = Option(TravisDomain.COM, case_sensitive=False),
    token: str = "",
):
    client = Travis(domain, token)

    def process(build: dict):
        directory = output / build["repository"]["slug"]
        directory.mkdir(parents=True, exist_ok=True)
        
        for job in client.jobs(build["id"]):
            with open(directory / f"{job['id']}.log", "w") as log:
                log.write(client.log(job["id"]) or "404")
            with open(directory / f"{job['id']}.json", "w") as configuration:
                dump(job["build"]["request"]["config"], configuration)

    def builds(owner: str, repository: str = "") -> Iterator[dict]:
        if repository:
            builds = client.builds(f"github/{owner}%2f{repository}")
        else:
            builds = (
                build
                for repository in client.repositories(owner)
                for build in client.builds(repository["id"])
            )

        for build in builds:
            yield delayed(process)(build)

    Parallel(backend="threading", n_jobs=concurrency, verbose=40)(
        builds(owner, repository)
    )


if __name__ == "__main__":
    application()
