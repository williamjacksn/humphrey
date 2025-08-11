import json
import pathlib

THIS_FILE = pathlib.PurePosixPath(
    pathlib.Path(__file__).relative_to(pathlib.Path().resolve())
)


def gen(content: dict, target: str):
    pathlib.Path(target).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target).write_text(
        json.dumps(content, indent=2, sort_keys=True), newline="\n"
    )


def gen_dependabot():
    target = ".github/dependabot.yaml"
    content = {
        "version": 2,
        "updates": [
            {
                "package-ecosystem": e,
                "allow": [{"dependency-type": "all"}],
                "directory": "/",
                "schedule": {"interval": "daily"},
            }
            for e in ["github-actions", "uv"]
        ],
    }
    gen(content, target)


def gen_publish_workflow():
    target = ".github/workflows/publish-release-to-pypi.yaml"
    content = {
        "env": {
            "description": f"This workflow ({target}) was generated from {THIS_FILE}",
        },
        "name": "Publish the release package to PyPI",
        "on": {"release": {"types": ["published"]}},
        "jobs": {
            "publish": {
                "name": "Publish the release package to PyPI",
                "runs-on": "ubuntu-latest",
                "environment": {
                    "name": "pypi-release",
                    "url": "https://pypi.org/p/humphrey",
                },
                "permissions": {"id-token": "write"},
                "steps": [
                    {"name": "Check out the repository", "uses": "actions/checkout@v4"},
                    {"name": "Publish the package to PyPI", "run": "sh ci/publish.sh"},
                ],
            }
        },
    }
    gen(content, target)


def main():
    gen_dependabot()
    gen_publish_workflow()


if __name__ == "__main__":
    main()
