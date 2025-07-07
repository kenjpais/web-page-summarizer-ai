import re
from typing import List, Tuple, Dict, Any
from rapidfuzz import fuzz, process


def clean_feature_name(feature_name: str) -> str:
    """Clean and normalize feature name for better matching."""
    # Remove parentheses and content inside them
    feature_name = re.sub(r"\([^)]*\)", "", feature_name)
    # Remove common prefixes/suffixes
    feature_name = re.sub(
        r"^(enable|disable|feature|gate)[-_]?", "", feature_name, flags=re.IGNORECASE
    )
    feature_name = re.sub(
        r"[-_]?(enable|disable|feature|gate)$", "", feature_name, flags=re.IGNORECASE
    )
    # Replace underscores and dashes with spaces
    feature_name = re.sub(r"[-_]", " ", feature_name)
    # Remove extra whitespace
    feature_name = " ".join(feature_name.split())
    return feature_name.strip()


def clean_jira_summary(summary: str) -> str:
    """Clean and normalize JIRA summary for better matching."""
    # Remove common JIRA prefixes
    summary = re.sub(
        r"^(story|task|bug|epic|feature)[-:]?\s*", "", summary, flags=re.IGNORECASE
    )
    # Remove ticket numbers/IDs
    summary = re.sub(r"^\w+-\d+[-:]?\s*", "", summary, flags=re.IGNORECASE)
    # Remove brackets and content
    summary = re.sub(r"\[[^\]]*\]", "", summary)
    # Remove extra whitespace
    summary = " ".join(summary.split())
    return summary.strip()


def calculate_match_score(feature_name: str, jira_summary: str) -> float:
    """Calculate comprehensive match score using multiple fuzzy matching algorithms."""
    # Clean both strings
    clean_feature = clean_feature_name(feature_name)
    clean_summary = clean_jira_summary(jira_summary)

    # Skip if either string is too short after cleaning
    if len(clean_feature) < 2 or len(clean_summary) < 2:
        return 0.0

    # Calculate different types of similarity
    ratio = fuzz.ratio(clean_feature, clean_summary)
    partial_ratio = fuzz.partial_ratio(clean_feature, clean_summary)
    token_sort_ratio = fuzz.token_sort_ratio(clean_feature, clean_summary)
    token_set_ratio = fuzz.token_set_ratio(clean_feature, clean_summary)

    # Weighted average (partial_ratio and token_set_ratio are more important)
    weights = [0.2, 0.4, 0.2, 0.2]
    scores = [ratio, partial_ratio, token_sort_ratio, token_set_ratio]

    weighted_score = sum(w * s for w, s in zip(weights, scores))

    # Boost score if feature name appears as a substring in the summary
    if clean_feature.lower() in clean_summary.lower():
        weighted_score = min(100, weighted_score * 1.2)

    return weighted_score


def fuzzy_match_features_to_jira(
    feature_names: List[str],
    jira_issues: List[Dict[str, Any]],
    threshold: float = 70.0,
    max_matches_per_feature: int = 3,
) -> List[Dict[str, Any]]:
    """
    Match feature names to JIRA issues using fuzzy matching.

    Args:
        feature_names: List of feature gate names
        jira_issues: List of JIRA issue dictionaries with 'key' and 'summary' fields
        threshold: Minimum similarity score (0-100) to consider a match
        max_matches_per_feature: Maximum number of matches to return per feature

    Returns:
        List of match dictionaries with feature_name, jira_key, jira_summary, and score
    """
    matches = []

    for feature_name in feature_names:
        print(f"Matching feature: {feature_name}")

        # Calculate scores for all JIRA issues
        issue_scores = []
        for issue in jira_issues:
            score = calculate_match_score(feature_name, issue.get("summary", ""))
            if score >= threshold:
                issue_scores.append(
                    {
                        "feature_name": feature_name,
                        "jira_key": issue.get("key", ""),
                        "jira_summary": issue.get("summary", ""),
                        "score": score,
                        "jira_issue": issue,
                    }
                )

        # Sort by score and take top matches
        issue_scores.sort(key=lambda x: x["score"], reverse=True)
        top_matches = issue_scores[:max_matches_per_feature]

        if top_matches:
            print(f"  Found {len(top_matches)} matches:")
            for match in top_matches:
                print(
                    f"    {match['jira_key']}: {match['jira_summary'][:60]}... (score: {match['score']:.1f})"
                )
        else:
            print(f"  No matches found above threshold {threshold}")

        matches.extend(top_matches)

    return matches


def get_best_match_per_feature(
    feature_names: List[str], jira_issues: List[Dict[str, Any]], threshold: float = 70.0
) -> Dict[str, Dict[str, Any]]:
    """
    Get the best JIRA match for each feature name.

    Args:
        feature_names: List of feature gate names
        jira_issues: List of JIRA issue dictionaries
        threshold: Minimum similarity score to consider a match

    Returns:
        Dictionary mapping feature_name to best match info
    """
    best_matches = {}

    for feature_name in feature_names:
        best_score = 0
        best_match = None

        for issue in jira_issues:
            score = calculate_match_score(feature_name, issue.get("summary", ""))
            if score >= threshold and score > best_score:
                best_score = score
                best_match = {
                    "jira_key": issue.get("key", ""),
                    "jira_summary": issue.get("summary", ""),
                    "score": score,
                    "jira_issue": issue,
                }

        if best_match:
            best_matches[feature_name] = best_match

    return best_matches


def find_jira_matches_for_features(
    feature_names: List[str], jira_issues: List[Dict[str, Any]], threshold: float = 70.0
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Find JIRA matches for features and return both matches and unmatched features.

    Args:
        feature_names: List of feature gate names
        jira_issues: List of JIRA issue dictionaries
        threshold: Minimum similarity score to consider a match

    Returns:
        Tuple of (matched_features, unmatched_features)
    """
    matches = fuzzy_match_features_to_jira(
        feature_names, jira_issues, threshold, max_matches_per_feature=1
    )
    matched_feature_names = {match["feature_name"] for match in matches}
    unmatched_features = [f for f in feature_names if f not in matched_feature_names]

    return matches, unmatched_features
