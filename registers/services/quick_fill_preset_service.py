from typing import Optional

from django.contrib.auth.models import User
from django.db.models import QuerySet

from registers.models import QuickFillPreset


class QuickFillPresetService:
    """Service for Quick Fill Preset CRUD operations."""

    RELATED_FIELDS = ('category', 'payment_method')

    def get_active_presets_for_user(self, user: User) -> QuerySet:
        """Returns active presets for a user, optimized with select_related."""
        return (
            QuickFillPreset.objects
            .filter(user=user, is_active=True)
            .select_related(*self.RELATED_FIELDS)
            .order_by('display_order', 'name')
        )

    def get_all_presets_for_user(self, user: User) -> QuerySet:
        """Returns all presets for a user (active and inactive)."""
        return (
            QuickFillPreset.objects
            .filter(user=user)
            .select_related(*self.RELATED_FIELDS)
            .order_by('display_order', 'name')
        )

    def get_preset_by_id_for_user(
        self, preset_id: int, user: User
    ) -> Optional[QuickFillPreset]:
        """Returns a specific preset with ownership verification."""
        try:
            return (
                QuickFillPreset.objects
                .select_related(*self.RELATED_FIELDS)
                .get(id=preset_id, user=user)
            )
        except QuickFillPreset.DoesNotExist:
            return None

    def create_preset(self, user: User, preset_data: dict) -> QuickFillPreset:
        """Creates a new preset for the user."""
        preset = QuickFillPreset(user=user, **preset_data)
        preset.save()
        return preset

    def delete_preset(self, preset_id: int, user: User) -> bool:
        """Deletes a preset. Returns True if deleted, False if not found."""
        preset = self.get_preset_by_id_for_user(preset_id, user)
        if preset is None:
            return False
        preset.delete()
        return True
