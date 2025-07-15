from dataclasses import dataclass, asdict


@dataclass
class GithubModel:
    """
    Standardized data model for GitHub items (PRs and commits).
    
    Attributes:
        id: Unique identifier (PR number for PRs, SHA for commits)
        type: Item type identifier ("pullRequest" or "commit")
        url: GitHub URL to the item (optional, can be reconstructed)
        title: PR title (for Pull Requests only)
        body: PR description/body content (for Pull Requests only)  
        message: Commit message (for commits only)
        
    The model uses optional fields to handle the differences between PR and
    commit data structures while maintaining a consistent interface.
    """
    id: str
    type: str
    url: str = ""
    title: str = ""
    body: str = ""
    message: str = ""

    def to_dict(self):
        """
        Convert the model to a dictionary, excluding empty fields.
        
        Returns:
            Dictionary containing only non-empty field values
            
        Example:
            For a PR: {"id": "123", "type": "pullRequest", "title": "Fix bug", "body": "..."}
            For a commit: {"id": "abc123", "type": "commit", "message": "Fix bug"}
        """
        return {k: v for k, v in asdict(self).items() if v}
