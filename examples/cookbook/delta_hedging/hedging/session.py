"""SDK login and environment guards shared by every subcommand."""
from __future__ import annotations

ENV_CHOICES = ("uat", "prod")


def login(env_name: str = "uat"):
    """Return an authenticated SDK client.

    Credentials come from PHONE_NO / MPIN in a local .env file
    (``env_creds=True``); the SDK prompts for the OTP and manages its own
    session store.
    """
    from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

    # UAT by default. To use production, switch to NubraEnv.PROD.
    env = NubraEnv.PROD if env_name == "prod" else NubraEnv.UAT
    return InitNubraSdk(env, env_creds=True)


def check_order_flags(env_name: str, place_orders: bool, allow_prod: bool) -> None:
    """Refuse to place orders on PROD unless ``--allow-prod`` was given too."""
    if place_orders and env_name == "prod" and not allow_prod:
        raise SystemExit(
            "Refusing to place orders on PROD without --allow-prod. "
            "Run on UAT first, or pass both --place-orders and --allow-prod."
        )


def rupees(paise) -> float:
    """Prices from the SDK are integer paise; convert to rupees (None -> 0.0)."""
    return (paise or 0) / 100.0
