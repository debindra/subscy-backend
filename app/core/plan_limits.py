from typing import Any, Dict


PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    "free": {
        "max_subscriptions": 5,
        "max_team_seats": 1,
        "analytics": {
            "monthly_trend": {
                "enabled": True,
                "max_months": 6,
            },
            "category_breakdown": False,  # Categorization locked behind Pro
        },
        "exports": {
            "csv": False,
            "pdf": False,
        },
        "business_profile": False,
        "categorization": False,  # Feature flag for categorization
        "smart_renewal_management": False,  # Feature flag for smart renewal management
        "cancellation_notes": False,  # Cancellation link/note storage
        "priority_support": False,
    },
    "pro": {
        "max_subscriptions": None,  # Unlimited
        "max_team_seats": 1,
        "analytics": {
            "monthly_trend": {
                "enabled": True,
                "max_months": 24,
            },
            "category_breakdown": True,
            "advanced": True,
        },
        "exports": {
            "csv": True,
            "pdf": True,
        },
        "business_profile": False,
        "categorization": True,  # Feature flag for categorization
        "smart_renewal_management": True,  # Feature flag for smart renewal management
        "cancellation_notes": True,  # Cancellation link/note storage
        "priority_support": True,
    },
    "family": {
        "max_subscriptions": None,  # Unlimited
        "max_team_seats": 5,  # Up to 5 linked user accounts
        "analytics": {
            "monthly_trend": {
                "enabled": True,
                "max_months": 24,
            },
            "category_breakdown": True,
            "advanced": True,
        },
        "exports": {
            "csv": True,
            "pdf": True,
        },
        "business_profile": False,
        "categorization": True,  # All Pro features
        "smart_renewal_management": True,
        "cancellation_notes": True,
        "priority_support": True,
        "shared_accounts": True,  # Family feature: shared subscription list
        "individual_dashboards": True,  # Family feature: separate user dashboards
    },
    # Legacy support for "personal" and "business" - map to new tiers
    "personal": {
        "max_subscriptions": 5,
        "max_team_seats": 1,
        "analytics": {
            "monthly_trend": {
                "enabled": True,
                "max_months": 6,
            },
            "category_breakdown": False,
        },
        "exports": {
            "csv": False,
            "pdf": False,
        },
        "business_profile": False,
        "categorization": False,
        "smart_renewal_management": False,
    },
    "business": {
        "max_subscriptions": None,  # Unlimited
        "max_team_seats": 10,
        "analytics": {
            "monthly_trend": {
                "enabled": True,
                "max_months": 24,
            },
            "category_breakdown": True,
            "advanced": True,
        },
        "exports": {
            "csv": True,
            "pdf": True,
        },
        "business_profile": True,
        "priority_support": True,
        "categorization": True,
        "smart_renewal_management": True,
    },
}


def get_plan_limits(account_type: str) -> Dict[str, Any]:
    return PLAN_LIMITS.get(account_type, PLAN_LIMITS["free"])


def ensure_feature(account_type: str, feature_path: str):
    """
    Ensure a feature flag is enabled for the provided account type.

    feature_path uses dot notation e.g. ``analytics.monthly_trend.enabled``.
    Raises ValueError if the feature is not available.
    """
    segments = feature_path.split(".")
    limits = get_plan_limits(account_type)
    value: Any = limits

    for segment in segments:
        if not isinstance(value, dict):
            value = None
            break
        value = value.get(segment)

    if value is True or (isinstance(value, (int, float)) and value > 0):
        return

    if value is None or value is False:
        raise ValueError(f"Feature '{feature_path}' is not available for {account_type} accounts.")

    # Fallback: treat any truthy value as allowed
    if value:
        return

    raise ValueError(f"Feature '{feature_path}' is not available for {account_type} accounts.")

