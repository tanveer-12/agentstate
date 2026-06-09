import os
import secrets

from fastapi import Header, HTTPException


def is_valid_key(key: str) -> bool:
    """Return true if the supplied API key is valid."""
    valid_keys = {
        k.strip()
        for k in os.environ.get(
            "AGENTSTATE_API_KEYS",
            "dev-key-123",
        ).split(",")
        if k.strip()
    }
    return key in valid_keys


def verify_api_key(
    x_api_key: str | None = Header(None),
) -> str:
    """
    FastAPI dependency for API key authentication.

    Inject with Depends(verify_api_key) on any protected endpoint.

    Keys are self-configured by whoever runs the server — set the
    AGENTSTATE_API_KEYS environment variable.

    There is no central key issuance.

    Generate a secure key with:

        python -c "import secrets; print(secrets.token_urlsafe(32))"
    """
    print("HEADER", repr(x_api_key))
    if not x_api_key or not is_valid_key(x_api_key):
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "invalid_api_key",
                "message": (
                    "Invalid or missing API key. "
                    "Set valid keys via the AGENTSTATE_API_KEYS "
                    "environment variable as a comma-separated list."
                ),
            },
        )
    return x_api_key


def generate_key() -> str:
    """Generate a cryptographically secure API Key."""
    return secrets.token_urlsafe(32)
