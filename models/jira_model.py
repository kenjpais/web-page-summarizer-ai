class JiraModel:
    def __init__(self, fields):
        self.id = getattr(fields, "id", "")
        self.url = getattr(fields, "url", "")
        self.project = getattr(fields, "project", "")
        self.parent = getattr(fields, "parent", "")
        self.issuelinks = [
            issuelink.id for issuelink in getattr(fields, "issuelinks", "")
        ]
        self.issuetype = fields.issuetype.name
        self.description = fields.description
        self.summary = fields.summary

    def to_dict(self):
        return {
            "id": self.id,
            "issuetype": self.issuetype,
            "description": self.description,
            "summary": self.summary,
            "parent": self.parent,
            "issuelinks": self.issuelinks,
        }
        """
        return {
            "id": self.id if self.id else "",
            "url": self.url,
            "project": (
                {
                    "key": getattr(self.project, "key", None),
                    "name": getattr(self.project, "name", None),
                    "id": getattr(self.project, "id", None),
                }
                if self.project
                else None
            ),
            "issuetype": (
                {
                    "name": getattr(self.issuetype, "name", None),
                    "id": getattr(self.issuetype, "id", None),
                }
                if self.issuetype
                else None
            ),
            "description": self.description,
            "summary": self.summary,
            "labels": self.labels,
            "resolution": (
                {
                    "name": getattr(self.resolution, "name", None),
                    "id": getattr(self.resolution, "id", None),
                }
                if self.resolution
                else None
            ),
        }
        """
