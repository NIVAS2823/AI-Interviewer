def sanitize_llm_output(obj):
    """
    Recursively replace None values with empty strings or empty lists.
    Prevents Pydantic validation failures.
    """
    if isinstance(obj, dict):
        return {k: sanitize_llm_output(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [sanitize_llm_output(item) for item in obj]

    if obj is None:
        return ""  # Convert None → empty string to avoid validation issues

    return obj
