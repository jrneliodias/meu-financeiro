from decimal import Decimal
import json
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder
import os


def convert_values_to_float(data):
    return {key: float(value) if isinstance(
        value, Decimal) else float(value) for key, value in data.items()}


def debug_to_json(data, filename_prefix, subfolder='debug_logs'):
    """
    Save debug data to a JSON file with timestamp in subfolder structure.

    Args:
        data: The data to be saved
        filename_prefix: The prefix for the filename (e.g., 'expense_calc')
        subfolder: The base subfolder to store debug files (default: 'debug_logs')

    Returns:
        str: Path to the created debug file
    """
    return None
    try:
        # Create timestamp for subfolder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create debug directory with timestamp
        debug_dir = os.path.join(
            os.getcwd(),
            subfolder,
            timestamp
        )
        os.makedirs(debug_dir, exist_ok=True)

        # Sanitize filename
        safe_filename = ''.join(c if c.isalnum() or c in ('-', '_') else '_'
                                for c in filename_prefix)

        # Create full filepath (now without timestamp in filename)
        filepath = os.path.join(
            debug_dir,
            f"{safe_filename}.json"
        )
        print(f"Attempting to write to: {filepath}")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'filename': filename_prefix,
                'data': data
            }, f, cls=DjangoJSONEncoder, indent=2)

        # print(f"Successfully wrote debug file to: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving debug file: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None
