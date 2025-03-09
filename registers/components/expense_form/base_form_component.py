from abc import ABC, abstractmethod
from django import forms


class BaseFormComponent(ABC):
    """Abstract base class for form components following Single Responsibility Principle"""
    @abstractmethod
    def get_initial_data(self):
        """Get initial data for the form"""
        pass

    @abstractmethod
    def get_form_fields(self):
        """Get form fields configuration"""
        pass
