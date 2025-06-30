from typing import List
import pandas as pd
from alert.data_source.base_data_source import BaseDataSource


class AlertGenerator:
    def __init__(self, data_source: BaseDataSource, threshold: List[float],
                 duration: int, duration_unit: str,
                 frequency: int,
                 time_window: int, time_window_unit: str):
        """
        Initializes the AlertGenerator with data source, threshold, duration, frequency, and time window.

        :param data_source: Data source object to monitor (replaces sensor).
        :param threshold: List of two float values representing the lower and upper thresholds.
        :param duration: Duration of the violation in seconds, minutes, or hours.
        :param duration_unit: Unit of the duration (s, m, h).
        :param frequency: Maximum number of violations allowed within the time window.
        :param time_window: Time window in seconds, minutes, or hours to monitor the violations.
        :param time_window_unit: Unit of the time window (s, m, h).
        """
        self.data_source = data_source
        self.alerts = []
        self.thresholds = []
        self.duration_in_seconds = 0
        self.frequency = 0
        self.violation_count = 0
        self.violation_timestamps = []
        self.violation_start_timestamp = None  # Timestamp of the first violation
        self.set_threshold(threshold)
        self.set_duration(duration, duration_unit)
        self.set_frequency(frequency)
        self.set_time_window(time_window, time_window_unit)
        self.alert_type = None

    def set_threshold(self, thresholds: List[float]):
        if not isinstance(thresholds, list) or len(thresholds) != 2:
            raise ValueError("Thresholds must be a list containing exactly two float values.")
        if thresholds[0] is None:
            thresholds[0] = float('-inf')
        if thresholds[1] is None:
            thresholds[1] = float('inf')
        if thresholds[0] > thresholds[1]:
            raise ValueError("The first threshold must be lower than the second.")
        self.thresholds = thresholds

    def set_duration(self, duration: int, unit: str):
        if unit not in ["s", "m", "h"]:
            raise ValueError("Unit must be one of 's', 'm', or 'h'.")
        self.duration = duration
        self.duration_unit = unit
        self.duration_in_seconds = self.__convert_to_seconds(duration, unit)

    def set_time_window(self, time_window: int, unit: str):
        if unit not in ["s", "m", "h"]:
            raise ValueError("Unit must be one of 's', 'm', or 'h'.")
        self.time_window = time_window
        self.time_window_unit = unit
        self.time_window_in_seconds = self.__convert_to_seconds(time_window, unit)

    def __convert_to_seconds(self, duration: int, unit: str):
        if unit == "s":
            return duration
        elif unit == "m":
            return duration * 60
        elif unit == "h":
            return duration * 3600

    def set_frequency(self, frequency: int):
        if frequency <= 0:
            raise ValueError("Frequency must be a positive integer.")
        self.frequency = frequency

    def detect_violations(self):
        """
        Detects continuous violations that exceed the minimum duration,
        and segments longer violations into smaller parts, merging remaining time with the last segment.

        Returns:
        - List of dictionaries, each containing details of a violation.
        """
        # Get data from data source
        df = self.data_source.data.sort_values('time').reset_index(drop=True)

        # Use the data_type from data source
        data_column = self.data_source.data_type

        # Mark rows where values are outside the thresholds
        df['violation'] = (df[data_column] < self.thresholds[0]) | (df[data_column] > self.thresholds[1])

        # If no violations, return an empty list
        if not df['violation'].any():
            return []

        # Identify groups of continuous violations
        df['violation_group'] = (df['violation'] != df['violation'].shift()).cumsum()

        violations = []
        for _, group in df[df['violation']].groupby('violation_group'):
            start_time = group['time'].iloc[0]
            end_time = group['time'].iloc[-1]
            total_duration = (end_time - start_time) / pd.Timedelta(1, unit=self.duration_unit)

            if total_duration > self.duration:
                # starting from the 2nd element, check if the violation duration is longer than the threshold
                segment_start = 0
                for segment_end in range(1, len(group)):
                    # If the duration of the violation is longer than the threshold, create a segment
                    if (group['time'].iloc[segment_end] - group['time'].iloc[segment_start]) / pd.Timedelta(1, unit=self.duration_unit) >= self.duration:
                        segment = group.iloc[segment_start:segment_end+1]
                        segment_violation_type = (
                            'low' if (segment[data_column] < self.thresholds[0]).all()
                            else 'high' if (segment[data_column] > self.thresholds[1]).all()
                            else 'mixed'
                        )
                        violations.append({
                            'start_time': segment['time'].iloc[0],
                            'end_time': segment['time'].iloc[-1],
                            'duration': (segment['time'].iloc[-1] - segment['time'].iloc[0]) / pd.Timedelta(1, unit=self.duration_unit),
                            'values': segment[data_column].tolist(),
                            'type': segment_violation_type
                        })
                        segment_start = segment_end
            else:
                segment_violation_type = (
                            'low' if (group[data_column] < self.thresholds[0]).all()
                            else 'high' if (group[data_column] > self.thresholds[1]).all()
                            else 'mixed'
                        )
                violations.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': total_duration,
                    'values': group[data_column].tolist(),
                    'type': segment_violation_type
                })

        return violations

    def raise_alarms(self, violations):
        """
        Checks if the number of violations exceeds the given frequency within the specified time window.

        Parameters:
        - violations: List of dictionaries, each containing 'start_time' and 'end_time' of a violation

        Returns:
        - List of alarms, each represented as a dictionary with details of the alarm
        """
        alarms = []
        if len(violations) == 0:
            return violations, alarms

        # Filter to only include violations with sufficient duration
        violations = [v for v in violations if v['duration'] >= self.duration]
        if len(violations) == 0:
            return violations, alarms

        # Ensure the list is sorted by the start time of each violation
        violations = sorted(violations, key=lambda x: x['start_time'])
        # Iterate over each subset of violations of length equal to the frequency
        for i in range(len(violations) - self.frequency + 1):
            # Get the start time of the first violation in the subset
            start_time = violations[i]['start_time']
            # Get the end time of the last violation in the subset
            end_time = violations[i + self.frequency - 1]['end_time']

            # alarm type
            alarm_type = (
                'mixed' if (
                    any(v['type'] == 'mixed' for v in violations[i:i + self.frequency]) or
                    (any(v['type'] == 'low' for v in violations[i:i + self.frequency]) and
                     any(v['type'] == 'high' for v in violations[i:i + self.frequency]))
                ) else 'low' if all(
                    v['type'] == 'low' for v in violations[i:i + self.frequency]
                ) else 'high'
            )

            # Check if the duration is within the time window
            if (end_time - start_time) / pd.Timedelta(1, unit=self.time_window_unit) <= self.time_window:
                alarm = {
                    'alarm_start_time': start_time,
                    'alarm_end_time': end_time,
                    'num_violations': self.frequency,
                    'max_duration': round(max(v['duration'] for v in violations[i:i + self.frequency]), 2),
                    'min_duration': round(min(v['duration'] for v in violations[i:i + self.frequency]), 2),
                    'avg_duration': round(sum(v['duration'] for v in violations[i:i + self.frequency]) / self.frequency, 2),
                    'type': alarm_type,
                    'violations': violations[i:i + self.frequency]
                }
                alarms.append(alarm)
        return violations, alarms

    def find_next_start_point(self, raw_violations, violations, alarms):
        """
        Finds the next start time for monitoring violations.

        Parameters:
        - raw_violations: List of dictionaries, each containing details of a violation
        - violations: List of dictionaries, each containing details of a violation that exceeds the minimum duration required
        - alarms: List of dictionaries, each containing details of an alarm

        Returns:
        - Timestamp for the next start time to monitor violations
        """
        recent_time = self.data_source.data['time'].max()
        next_start_time = recent_time # default to the most recent time, if no alarms are raised AND no violations are detected
        if len(alarms) == 0: # if no alarms are raised, start from the last time a threshold condition was met
            start_from_violation = - (self.frequency - 1)
            if len(violations[start_from_violation:]) > 0: # if number of violations is less than the frequency so that no alarm is made, start from the first violation
                for violation in violations:
                    # if the violation is within the time window, start from the start time of the violation
                    if recent_time -  violation['start_time'] < pd.Timedelta(self.time_window, unit=self.time_window_unit):
                        next_start_time = violation['start_time']
                        break
            elif len(raw_violations) > 0: # if no violations are detected or violation are too old, start from the last time a threshold condition was met
                next_start_time = raw_violations[-1]['start_time']
        else: # if alarms are raised
            next_start_time = alarms[-1]['alarm_end_time'] # start from the end time of the last alarm
        return next_start_time

    def get_deviation_from_standard(self, min_value, max_value):
        """
        Calculates the deviation of the violation from the industry standard.

        Parameters:
        - min_value: Minimum value of the violation
        - max_value: Maximum value of the violation

        Returns:
        - Tuple containing the deviation from the industry standard
        """
        if self.data_source.industry_standard is None:
            return None
        min_deviation = 0
        max_deviation = 0

        if min_value >= self.data_source.industry_standard[0] and min_value <= self.data_source.industry_standard[1]:
            min_deviation = 0
        else:
            if min_value < self.data_source.industry_standard[0]:
                min_deviation = min_value - self.data_source.industry_standard[0]
            else:
                min_deviation = min_value - self.data_source.industry_standard[1]
        if max_value >= self.data_source.industry_standard[0] and max_value <= self.data_source.industry_standard[1]:
            max_deviation = 0
        else:
            if max_value < self.data_source.industry_standard[0]:
                max_deviation = max_value - self.data_source.industry_standard[0]
            else:
                max_deviation = max_value - self.data_source.industry_standard[1]
        return tuple([min_deviation, max_deviation])

    def severity_level(self, min_value, max_value, type):
        """
        Determines the severity level based on the deviation from the normal range.

        Parameters:
        - min_value: Minimum value of the violation
        - max_value: Maximum value of the violation
        - type: Type of violation (low, high, mixed)

        Returns:
        - String representing the severity level
        """
        severity = 'low'
        if type == 'high':
            if min_value > self.data_source.percentile_75th:
                severity = 'medium'
            if min_value > self.data_source.percentile_90th:
                severity = 'high'
        elif type == 'low':
            if max_value < self.data_source.percentile_25th:
                severity = 'medium'
            if max_value < self.data_source.percentile_10th:
                severity = 'high'
        elif type == 'mixed':
            if (max_value - min_value) > (self.data_source.percentile_75th - self.data_source.percentile_25th):
                severity = 'medium'
            if (max_value - min_value) > (self.data_source.percentile_90th - self.data_source.percentile_10th):
                severity = 'high'
        if self.data_source.industry_standard:
            if max_value > self.data_source.industry_standard[1] or min_value < self.data_source.industry_standard[0]:
                severity = 'high'
        return severity

    def make_alert(self, alarms):
        # we need all the details in the alert
        # timestamp, sensor_id, sensor_type, sensor_name, equipment, location, type, severity,
        # deviation from normal, deviation from industry standard, min_duration, max_duration, avg_duration, max_frequency
        if not self.thresholds or (self.duration_in_seconds is None) or self.frequency <= 0:
            raise ValueError("Thresholds, duration, and frequency must be set before checking for alerts.")
        if len(alarms) == 0:
            return
        for alarm in alarms:
            start_timestamp = alarm['alarm_start_time']
            end_timestamp = alarm['alarm_end_time']
            max_frequency = alarm['num_violations']
            max_values = [max(v['values']) for v in alarm['violations']]
            min_values = [min(v['values']) for v in alarm['violations']]
            deviation_from_normal = tuple([min(min_values) - self.data_source.percentile_50th, max(max_values) - self.data_source.percentile_50th])
            deviation_from_industry = self.get_deviation_from_standard(min(min_values), max(max_values))
            severity = self.severity_level(min(min_values), max(max_values), alarm['type'])
            alert = {
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'sensor_id': self.data_source.sensor_id,
                'data_type': self.data_source.data_type,
                'alarm_type': alarm['type'],
                'severity': severity,
                'max_deviation_from_normal': max(deviation_from_normal),
                'min_deviation_from_normal': min(deviation_from_normal),
                'max_deviation_from_industry': max(deviation_from_industry) if deviation_from_industry else None,
                'min_deviation_from_industry': min(deviation_from_industry) if deviation_from_industry else None,
                'min_duration': alarm['min_duration'],
                'max_duration': alarm['max_duration'],
                'avg_duration': alarm['avg_duration'],
                'frequency': max_frequency,
                'status': 0
            }
            yield alert