from dataclasses import dataclass
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import date


@dataclass
class QuickFillOption:
    """Data class for quick fill options."""
    name: str
    description: str
    category_id: Optional[int]
    payment_method_id: Optional[int]
    icon: str
    date: date
    default_amount: Decimal = Decimal('0')


class QuickFillMenu:
    """Quick fill menu that loads presets from database."""

    def __init__(self, user=None):
        self._options: Dict[str, QuickFillOption] = {}
        if user:
            self._load_presets_from_database(user)

    def _load_presets_from_database(self, user):
        """Load active presets from database for the given user."""
        from registers.models import QuickFillPreset

        active_presets = (
            QuickFillPreset.objects
            .filter(user=user, is_active=True)
            .select_related('category', 'payment_method')
            .order_by('display_order', 'name')
        )
        for preset in active_presets:
            option = QuickFillOption(
                name=preset.name,
                description=preset.description,
                category_id=preset.category_id,
                payment_method_id=preset.payment_method_id,
                icon=preset.icon,
                default_amount=preset.default_amount,
                date=date.today(),
            )
            self.register_option(str(preset.id), option)

    def register_option(self, key: str, option: QuickFillOption):
        """Register a new quick fill option."""
        self._options[key] = option

    def get_option(self, key: str) -> Optional[QuickFillOption]:
        """Get a quick fill option by key."""
        return self._options.get(key)

    def get_all_options(self) -> List[QuickFillOption]:
        """Get all registered quick fill options."""
        return list(self._options.values())

    def get_all_options_with_keys(self) -> Dict[str, QuickFillOption]:
        """Get all options as key -> option dict for template rendering."""
        return dict(self._options)
