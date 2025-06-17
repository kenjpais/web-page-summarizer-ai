class GithubModel:
    def __init__(self, id, url="", title="", body="", message=""):
        self.id = id
        self.url = url
        self.title = title
        self.body = body
        self.message = message

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "message": self.message,
        }
