def classify(error: Exception) -> dict:
    # Side effects are never retried here; only safe reads may use a bounded retry.
    return {"kind":"permanent","retry_safe":False,"message":str(error)[:240]}
