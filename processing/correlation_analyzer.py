from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from scipy import stats
from models.base_models import Location
from models.insights_models import CorrelationInsight


class CorrelationAnalyzer:
    """Analyzes correlations between different variables and locations"""

    def __init__(self):
        self.min_correlation_threshold = 0.5  # Minimum correlation to consider significant
        self.lag_windows = [0, 1, 2, 4, 8, 12, 24]  # Hours to check for lag correlations

    def analyze_correlations(self, data_dict: Dict[str, pd.DataFrame]) -> List[CorrelationInsight]:
        """Analyze correlations between all variables"""
        correlations = []

        # Combine all data into a single DataFrame for analysis
        combined_df = self._prepare_combined_dataframe(data_dict)

        if combined_df.empty:
            return correlations

        # Analyze same-location correlations
        location_groups = combined_df.groupby('location')
        for location, loc_data in location_groups:
            correlations.extend(self._analyze_location_correlations(location, loc_data))

        # Analyze cross-location correlations (adjacent areas)
        correlations.extend(self._analyze_cross_location_correlations(combined_df))

        return correlations

    def _prepare_combined_dataframe(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Prepare a combined DataFrame from multiple data sources"""
        frames = []

        for data_type, df in data_dict.items():
            if df.empty:
                continue

            # Standardize column names
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')

            # Add data type prefix to columns
            df.columns = [f"{data_type}_{col}" for col in df.columns]

            # Add location if not present
            if 'location' not in df.columns:
                df['location'] = 'default'

            frames.append(df)

        if not frames:
            return pd.DataFrame()

        # Combine all frames
        combined = pd.concat(frames, axis=1, join='outer')
        combined = combined.reset_index()

        return combined

    def _analyze_location_correlations(self, location: str,
                                     data: pd.DataFrame) -> List[CorrelationInsight]:
        """Analyze correlations within a single location"""
        correlations = []

        # Get numeric columns only
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()

        # Remove timestamp and location columns if present
        numeric_cols = [col for col in numeric_cols
                       if col not in ['timestamp', 'location', 'index']]

        # Calculate correlation matrix
        if len(numeric_cols) < 2:
            return correlations

        corr_matrix = data[numeric_cols].corr()

        # Extract significant correlations
        for i, var1 in enumerate(numeric_cols):
            for j, var2 in enumerate(numeric_cols):
                if i >= j:  # Skip diagonal and duplicate pairs
                    continue

                corr_value = corr_matrix.loc[var1, var2]

                if abs(corr_value) >= self.min_correlation_threshold:
                    # Check for lag correlations
                    best_lag = self._find_best_lag(data[var1], data[var2])

                    # Parse location
                    loc_obj = self._parse_location_string(location)

                    insight = CorrelationInsight(
                        variable1=var1,
                        variable1_location=loc_obj,
                        variable2=var2,
                        variable2_location=loc_obj,
                        correlation_coefficient=round(corr_value, 3),
                        relationship_type='positive' if corr_value > 0 else 'negative',
                        strength=self._get_correlation_strength(abs(corr_value)),
                        lag_hours=best_lag
                    )
                    correlations.append(insight)

        return correlations

    def _analyze_cross_location_correlations(self, data: pd.DataFrame) -> List[CorrelationInsight]:
        """Analyze correlations between adjacent locations"""
        correlations = []

        # This would be more sophisticated in production
        # For now, simplified version
        locations = data['location'].unique()

        for i, loc1 in enumerate(locations):
            for j, loc2 in enumerate(locations):
                if i >= j:
                    continue

                # Check if locations are adjacent (simplified logic)
                if self._are_locations_adjacent(loc1, loc2):
                    loc1_data = data[data['location'] == loc1]
                    loc2_data = data[data['location'] == loc2]

                    # Find common variables
                    loc1_vars = loc1_data.select_dtypes(include=[np.number]).columns
                    loc2_vars = loc2_data.select_dtypes(include=[np.number]).columns
                    common_vars = set(loc1_vars) & set(loc2_vars)

                    for var in common_vars:
                        if var in ['timestamp', 'location', 'index']:
                            continue

                        # Align data by timestamp
                        merged = pd.merge(
                            loc1_data[['timestamp', var]].rename(columns={var: f'{var}_1'}),
                            loc2_data[['timestamp', var]].rename(columns={var: f'{var}_2'}),
                            on='timestamp',
                            how='inner'
                        )

                        if len(merged) > 10:
                            corr_value = merged[f'{var}_1'].corr(merged[f'{var}_2'])

                            if abs(corr_value) >= self.min_correlation_threshold:
                                loc1_obj = self._parse_location_string(loc1)
                                loc2_obj = self._parse_location_string(loc2)

                                insight = CorrelationInsight(
                                    variable1=var,
                                    variable1_location=loc1_obj,
                                    variable2=var,
                                    variable2_location=loc2_obj,
                                    correlation_coefficient=round(corr_value, 3),
                                    relationship_type='positive' if corr_value > 0 else 'negative',
                                    strength=self._get_correlation_strength(abs(corr_value)),
                                    lag_hours=0
                                )
                                correlations.append(insight)

        return correlations

    def _find_best_lag(self, series1: pd.Series, series2: pd.Series) -> int:
        """Find the lag that produces the highest correlation"""
        best_lag = 0
        best_corr = series1.corr(series2)

        for lag in self.lag_windows[1:]:
            if lag >= len(series1):
                continue

            # Shift series2 by lag
            lagged_corr = series1[:-lag].corr(series2[lag:])

            if abs(lagged_corr) > abs(best_corr):
                best_corr = lagged_corr
                best_lag = lag

        return best_lag

    def _get_correlation_strength(self, corr_value: float) -> str:
        """Categorize correlation strength"""
        if corr_value >= 0.8:
            return 'strong'
        elif corr_value >= 0.6:
            return 'moderate'
        else:
            return 'weak'

    def _parse_location_string(self, location_str: str) -> Location:
        """Parse location string back to Location object"""
        if ' > ' in location_str:
            parts = location_str.split(' > ')
        else:
            parts = [location_str]

        return Location(
            country=parts[0] if len(parts) > 0 else '',
            city=parts[1] if len(parts) > 1 else '',
            building=parts[2] if len(parts) > 2 else '',
            floor=parts[3] if len(parts) > 3 else '',
            area=parts[4] if len(parts) > 4 else None
        )

    def _are_locations_adjacent(self, loc1: str, loc2: str) -> bool:
        """Check if two locations are adjacent (simplified)"""
        # In production, this would use actual building layout data
        # For now, check if they're on the same floor or adjacent floors
        parts1 = loc1.split(' > ')
        parts2 = loc2.split(' > ')

        if len(parts1) < 4 or len(parts2) < 4:
            return False

        # Same building
        if parts1[2] != parts2[2]:
            return False

        # Check floors
        try:
            floor1 = int(parts1[3].replace('Floor ', ''))
            floor2 = int(parts2[3].replace('Floor ', ''))
            return abs(floor1 - floor2) <= 1
        except:
            return parts1[3] == parts2[3]  # Same floor