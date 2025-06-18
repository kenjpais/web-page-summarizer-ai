class GithubModel:
    def __init__(self, id, type, url="", title="", body="", message=""):
        self.id = str(id)
        self.type = type
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
