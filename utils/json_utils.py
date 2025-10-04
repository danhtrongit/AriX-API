import pandas as pd
import numpy as np
from datetime import datetime
import json
import warnings

# Suppress pandas duplicate columns warning
warnings.filterwarnings('ignore', message='DataFrame columns are not unique')

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean DataFrame by removing duplicate columns
    """
    if df is None or df.empty:
        return df
    
    # Check for duplicate columns
    if df.columns.duplicated().any():
        # Keep first occurrence of duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
    
    return df

def serialize_data(data):
    """
    Convert pandas/numpy data types to JSON serializable formats
    Handle NaN values and duplicate columns properly
    """
    if isinstance(data, dict):
        return {key: serialize_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_data(item) for item in data]
    elif isinstance(data, pd.Timestamp):
        return data.isoformat()
    elif isinstance(data, (pd.Series, pd.DataFrame)):
        if isinstance(data, pd.DataFrame):
            # Clean duplicate columns before converting
            data = clean_dataframe(data)
            return serialize_data(data.to_dict('records'))
        else:
            return serialize_data(data.to_dict())
    elif isinstance(data, (np.integer, np.floating)):
        # Handle NaN values for numpy floats
        if np.isnan(data):
            return None
        # Use float() to preserve full precision instead of item()
        return float(data) if isinstance(data, np.floating) else int(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif pd.isna(data) or (isinstance(data, float) and np.isnan(data)):
        return None
    elif data is None:
        return None
    elif hasattr(data, 'isoformat'):  # datetime objects
        return data.isoformat()
    elif hasattr(data, 'item'):  # numpy scalar types
        try:
            value = data.item()
            # Check if the item is NaN
            if isinstance(value, float) and np.isnan(value):
                return None
            return value
        except (ValueError, OverflowError):
            return None
    else:
        # Final check for any remaining NaN values
        try:
            if isinstance(data, float) and (np.isnan(data) or data != data):  # NaN check
                return None
        except (TypeError, ValueError):
            pass
        return data

class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for pandas and numpy types with NaN handling
    """
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj):
                return None
            # Use float() to preserve full precision
            return float(obj) if isinstance(obj, np.floating) else int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        elif isinstance(obj, float) and (np.isnan(obj) or obj != obj):
            return None
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'item'):
            try:
                value = obj.item()
                if isinstance(value, float) and np.isnan(value):
                    return None
                return value
            except (ValueError, OverflowError):
                return None
        return super().default(obj)