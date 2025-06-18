from dataclasses import dataclass, asdict


@dataclass
class GithubModel:
    id: str
    type: str
    url: str = ""
    title: str = ""
    body: str = ""
    message: str = ""

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v}
