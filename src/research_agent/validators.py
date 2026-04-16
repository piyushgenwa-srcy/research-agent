from __future__ import annotations

from typing import List

from .models import ClientProfile, MarketAssortmentContext


def validate_client_profile(profile: ClientProfile) -> List[str]:
    errors: List[str] = []
    required_scalar_fields = [
        ("platform", profile.platform),
        ("client_name", profile.client_name),
        ("trend_definition", profile.trend_definition),
        ("price_bracket", profile.price_bracket),
        ("output_mode", profile.output_mode),
        ("use_case", profile.use_case),
        ("ship_to", profile.ship_to),
    ]
    for name, value in required_scalar_fields:
        if not value:
            errors.append(f"client_profile.{name} is required")
    if not profile.markets:
        errors.append("client_profile.markets must not be empty")
    if not profile.categories:
        errors.append("client_profile.categories must not be empty")
    if len(profile.trend_definition.strip()) < 25:
        errors.append("client_profile.trend_definition is too short to guide the run")
    return errors


def validate_market_context(context: MarketAssortmentContext) -> List[str]:
    errors: List[str] = []
    if not context.platform:
        errors.append("market_assortment_context.platform is required")
    if not context.markets:
        errors.append("market_assortment_context.markets must not be empty")
    if not context.focus_categories:
        errors.append("market_assortment_context.focus_categories must not be empty")
    return errors
