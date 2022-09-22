import json

from pathlib import Path
from typer import Typer, Option
from joblib import Parallel, delayed

from .travis import Travis, TravisHost


application = Typer(add_completion=False)


@application.command()
def main(
    owner: str,
    output: Path = Option(
        ...,
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    concurrency: int = 32,
    host: TravisHost = TravisHost.COM,
    token: str = "",
):
    client = Travis(host, token)

    def process(build: dict):
        for job in client.jobs(build["id"]):
            with open(output / f"{job['id']}.log", "w") as log:
                log.write(client.log(job["id"]))
            with open(output / f"{job['id']}.json", "w") as configuration:
                json.dump(job["build"]["request"]["config"], configuration)
 
    def builds(owner: str) -> iter:
        for repository in client.repositories(owner):
            for build in client.builds(repository["id"]):
                yield delayed(process)(build)

    output.mkdir(parents=True, exist_ok=True)
    Parallel(backend="threading", n_jobs=concurrency, verbose=40)(builds(owner))


if __name__ == "__main__":
    application()
