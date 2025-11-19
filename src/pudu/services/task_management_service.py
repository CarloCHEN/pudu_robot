import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pudu.rds.rdsTable import RDSTable

logger = logging.getLogger(__name__)

class TaskManagementService:
    """
    Service to handle the relationship between ongoing tasks and completed task reports.

    Key responsibilities:
    1. Upsert ongoing tasks (update existing or insert new)
    2. Update ongoing tasks to completed when final reports arrive from get_schedule_table()
    3. Handle time overlap detection between estimated and actual times
    """
    @staticmethod
    def manage_ongoing_tasks_complete(table: RDSTable, ongoing_tasks_data: List[dict], robots_needing_cleanup: List[str]):
        """
        Complete management of ongoing tasks:
        1. Upsert ongoing tasks from API data
        2. Cleanup ongoing tasks for robots not in API data

        Args:
            table: Database table instance
            ongoing_tasks_data: List of ongoing task data from API
            robots_needing_cleanup: List of robot SNs that need cleanup (no ongoing tasks from API)

        Returns:
            Dict[str, Dict]: Changes detected from upsert operations only (cleanup doesn't generate notifications)
        """
        all_changes = {}

        # 1. Process robots with ongoing tasks (upsert) - track changes for notifications
        if ongoing_tasks_data:
            upsert_changes = TaskManagementService._upsert_ongoing_tasks(table, ongoing_tasks_data)
            all_changes.update(upsert_changes)

        # 2. Cleanup robots without ongoing tasks - no change tracking needed
        if robots_needing_cleanup:
            TaskManagementService._cleanup_ongoing_tasks_for_robots(table, robots_needing_cleanup)

        return all_changes

    @staticmethod
    def _cleanup_ongoing_tasks_for_robots(table: RDSTable, robot_sns: List[str]):
        """
        Cleanup ongoing tasks for robots that no longer have ongoing tasks from API

        Args:
            table: Database table instance
            robot_sns: List of robot serial numbers to cleanup

        Note: No change tracking needed since cleanup operations don't generate notifications
        """
        if not robot_sns:
            return

        # Escape and safely format robot_sn list for SQL IN clause
        robot_placeholders = "', '".join([str(sn).replace("'", "''") for sn in robot_sns])

        try:
            # Batch check query
            check_query = f"""
                SELECT robot_sn, COUNT(*) AS task_count
                FROM {table.table_name}
                WHERE robot_sn IN ('{robot_placeholders}')
                  AND is_report = 0
                GROUP BY robot_sn
            """
            result = table.query_data(check_query)

            # Extract robots with ongoing tasks
            robots_with_tasks = []
            task_counts = {}

            for row in result:
                if isinstance(row, tuple):
                    robot_sn, count = row[0], row[1]
                elif isinstance(row, dict):
                    robot_sn = row.get('robot_sn')
                    count = row.get('task_count') or row.get('COUNT(*)', 0)
                else:
                    continue

                if robot_sn and count > 0:
                    robots_with_tasks.append(robot_sn)
                    task_counts[robot_sn] = count

            if not robots_with_tasks:
                logger.info(f"No ongoing tasks found for any of the {len(robot_sns)} robots")
                return

            # Batch delete query
            robots_to_delete = "', '".join([str(sn).replace("'", "''") for sn in robots_with_tasks])
            delete_query = f"""
                DELETE FROM {table.table_name}
                WHERE robot_sn IN ('{robots_to_delete}')
                  AND is_report = 0
            """
            table.query_data(delete_query)

            # Log details
            total_tasks_cleaned = sum(task_counts.values())
            logger.info(f"Cleaned up {total_tasks_cleaned} ongoing tasks for {len(robots_with_tasks)} robots")

            # Debug robots with no tasks
            robots_with_no_tasks = [r for r in robot_sns if r not in robots_with_tasks]
            if robots_with_no_tasks:
                logger.debug(f"No ongoing tasks to cleanup for {len(robots_with_no_tasks)} robots")

        except Exception as e:
            logger.warning(f"Batch cleanup failed, falling back to individual processing: {e}")

            failed_robots = []
            cleaned_up_robots = []

            for robot_sn in robot_sns:
                try:
                    # Individual check query
                    check_query = f"""
                        SELECT COUNT(*) AS cnt
                        FROM {table.table_name}
                        WHERE robot_sn = '{robot_sn.replace("'", "''")}'
                          AND is_report = 0
                    """
                    result = table.query_data(check_query)

                    count = 0
                    if result:
                        if isinstance(result[0], tuple):
                            count = result[0][0]
                        elif isinstance(result[0], dict):
                            count = result[0].get('cnt', 0) or result[0].get('COUNT(*)', 0)
                        elif isinstance(result[0], int):
                            count = result[0]

                    if count > 0:
                        delete_query = f"""
                            DELETE FROM {table.table_name}
                            WHERE robot_sn = '{robot_sn.replace("'", "''")}'
                              AND is_report = 0
                        """
                        table.query_data(delete_query)
                        cleaned_up_robots.append(robot_sn)

                except Exception as individual_error:
                    failed_robots.append(robot_sn)
                    logger.warning(f"Failed to cleanup ongoing tasks for robot {robot_sn}: {individual_error}")

            if cleaned_up_robots:
                logger.info(f"Individually cleaned up ongoing tasks for {len(cleaned_up_robots)} robots")
            if failed_robots:
                logger.error(f"Failed to cleanup ongoing tasks for {len(failed_robots)} robots: {failed_robots}")

    @staticmethod
    def _upsert_ongoing_tasks(table: RDSTable, ongoing_tasks_data: List[dict]):
        """
        Upsert ongoing tasks: update existing ongoing task or insert new one.
        Logic: Robot can only have 1 ongoing task, so update the most recent ongoing task if exists.

        Returns:
            Dict[str, Dict]: Changes detected in format compatible with change detection system
        """
        processed_robots = set()
        changes_detected = {}

        for ongoing_task in ongoing_tasks_data:
            try:
                robot_sn = ongoing_task['robot_sn']

                # Skip if we already processed this robot in this batch
                if robot_sn in processed_robots:
                    continue
                processed_robots.add(robot_sn)

                # Find existing ongoing task for this robot (most recent one)
                existing_query = f"""
                    SELECT id, task_id, task_name, status, start_time
                    FROM {table.table_name}
                    WHERE robot_sn = '{robot_sn}'
                    AND is_report = 0
                    ORDER BY start_time DESC
                    LIMIT 1
                """

                existing_results = table.query_data(existing_query)

                if existing_results:
                    # Update existing ongoing task
                    existing_record = existing_results[0]
                    existing_id = existing_record[0] if isinstance(existing_record, tuple) else existing_record.get('id')
                    existing_task_id = existing_record[1] if isinstance(existing_record, tuple) else existing_record.get('task_id')
                    existing_task_name = existing_record[2] if isinstance(existing_record, tuple) else existing_record.get('task_name')
                    existing_status = existing_record[3] if isinstance(existing_record, tuple) else existing_record.get('status')

                    # Check if this is the same task or a new task
                    if (existing_task_id == ongoing_task['task_id'] and
                        existing_task_name == ongoing_task['task_name']):
                        # Same task - update progress and other fields
                        TaskManagementService._update_ongoing_task_progress(table, existing_id, ongoing_task)

                        # Create change record for update
                        unique_id = f"{robot_sn}_{ongoing_task['task_id']}_{ongoing_task['start_time']}"
                        changes_detected[unique_id] = {
                            'robot_sn': robot_sn,
                            'primary_key_values': {
                                'robot_sn': robot_sn,
                                'task_name': ongoing_task['task_name'],
                                'start_time': ongoing_task['start_time']
                            },
                            'change_type': 'update',
                            'changed_fields': ['progress', 'status'] if existing_status != ongoing_task['status'] else ['progress'],
                            'old_values': {},
                            'new_values': ongoing_task,
                            'database_key': existing_id
                        }

                        logger.debug(f"✅ Updated ongoing task progress for robot {robot_sn}: {ongoing_task.get('progress', 0)}%")
                    else:
                        # Different task - delete old task and insert new one
                        TaskManagementService._delete_ongoing_task(table, robot_sn, existing_task_name)
                        logger.info(f"🗑️ Deleted ongoing task for robot {robot_sn}: {existing_task_name} before inserting new one")

                        # Insert new task
                        new_id = TaskManagementService._insert_new_ongoing_task_with_id(table, ongoing_task)
                        logger.info(f"🆕 Inserted new ongoing task for robot {robot_sn}: {ongoing_task['task_name']} with id: {new_id}")

                        # Create change record for new task
                        unique_id = f"{robot_sn}_{ongoing_task['task_id']}_{ongoing_task['start_time']}"
                        changes_detected[unique_id] = {
                            'robot_sn': robot_sn,
                            'primary_key_values': {
                                'robot_sn': robot_sn,
                                'task_name': ongoing_task['task_name'],
                                'start_time': ongoing_task['start_time']
                            },
                            'change_type': 'new_record',
                            'changed_fields': list(ongoing_task.keys()),
                            'old_values': {},
                            'new_values': ongoing_task,
                            'database_key': new_id
                        }
                else:
                    # No existing ongoing task - insert new one
                    new_id = TaskManagementService._insert_new_ongoing_task_with_id(table, ongoing_task)
                    logger.info(f"🆕 Inserted new ongoing task for robot (no existing task) {robot_sn}: {ongoing_task['task_name']} with id: {new_id}")

                    # Create change record for new task
                    unique_id = f"{robot_sn}_{ongoing_task['task_id']}_{ongoing_task['start_time']}"
                    changes_detected[unique_id] = {
                        'robot_sn': robot_sn,
                        'primary_key_values': {
                            'robot_sn': robot_sn,
                            'task_name': ongoing_task['task_name'],
                            'start_time': ongoing_task['start_time']
                        },
                        'change_type': 'new_record',
                        'changed_fields': list(ongoing_task.keys()),
                        'old_values': {},
                        'new_values': ongoing_task,
                        'database_key': new_id
                    }

            except Exception as e:
                logger.warning(f"⚠️ Error upserting ongoing task for robot {robot_sn}: {e}")

        return changes_detected

    @staticmethod
    def _delete_ongoing_task(table: RDSTable, robot_sn: str, task_name: str):
        """Delete an ongoing task."""
        query = f"""
            DELETE FROM {table.table_name}
            WHERE robot_sn = '{robot_sn}'
            AND task_name = '{task_name}'
            AND is_report = 0
        """
        table.query_data(query)
        logger.info(f"🗑️ Deleted ongoing task for robot {robot_sn}: {task_name}")

    @staticmethod
    def _insert_new_ongoing_task_with_id(table: RDSTable, ongoing_task: dict):
        """Insert a new ongoing task and return the database ID."""
        try:
            # Ensure is_report is set to 0
            ongoing_task['is_report'] = 0

            # Use batch_insert_with_ids to get the ID back
            ids = table.batch_insert_with_ids([ongoing_task])
            if ids:
                return ids[0][1]  # Return the database ID
            else:
                logger.error(f"❌ Inserted new ongoing task but no ID returned: {ongoing_task}; ids: {ids}")
            return None

        except Exception as e:
            logger.error(f"❌ Error inserting new ongoing task: {e}")
            return None

    @staticmethod
    def _update_ongoing_task_progress(table: RDSTable, record_id: int, ongoing_task: dict):
        """Update existing ongoing task with latest progress and data."""
        try:
            updates = {
                'progress': str(ongoing_task.get('progress', 0)),
                'actual_area': str(ongoing_task.get('actual_area', 0)),
                'duration': str(ongoing_task.get('duration', 0)),
                'efficiency': str(ongoing_task.get('efficiency', 0)),
                'remaining_time': str(ongoing_task.get('remaining_time', 0)),
                'battery_usage': str(ongoing_task.get('battery_usage', 0)),
                'consumption': str(ongoing_task.get('consumption', 0)),
                'water_consumption': str(ongoing_task.get('water_consumption', 0)),
                'status': str(ongoing_task.get('status', 'In Progress'))
            }
            if ongoing_task.get('status', '').lower() in ['in progress', 'task ended']:
                # Update estimated end time if task is in progress or task ended
                updates['end_time'] = str(ongoing_task.get('end_time', ''))

            for field, value in updates.items():
                table.update_field_by_filters(field, value, {'id': record_id})

        except Exception as e:
            logger.error(f"❌ Error updating ongoing task progress {record_id}: {e}")

    @staticmethod
    def _insert_new_ongoing_task(table: RDSTable, ongoing_task: dict):
        """Insert a new ongoing task."""
        try:
            # Ensure is_report is set to 0
            ongoing_task['is_report'] = 0
            table.insert_data(ongoing_task)

        except Exception as e:
            logger.error(f"❌ Error inserting new ongoing task: {e}")

    @staticmethod
    def update_ongoing_tasks_to_completed(table: RDSTable, completed_tasks_data: List[dict]):
        """
        For each completed task, find matching ongoing tasks and update them.
        If multiple ongoing tasks match by task_id, find the one with largest time overlap.
        """
        for completed_task in completed_tasks_data:
            try:
                robot_sn = completed_task['robot_sn']
                task_id = completed_task['task_id']
                task_name = completed_task['task_name']
                completed_start = pd.to_datetime(completed_task['start_time'])
                completed_end = pd.to_datetime(completed_task['end_time'])

                # Get ALL ongoing tasks with matching task_id
                task_id_query = f"""
                    SELECT id, start_time, end_time FROM {table.table_name}
                    WHERE robot_sn = '{robot_sn}'
                    AND task_id = '{task_id}'
                    AND is_report = 0
                    ORDER BY start_time DESC
                """

                task_id_results = table.query_data(task_id_query)

                if task_id_results:
                    # Find the ongoing task with largest time overlap
                    best_match = None
                    best_overlap_duration = timedelta(0)

                    for result in task_id_results:
                        record_id = result[0] if isinstance(result, tuple) else result.get('id')
                        db_start_str = result[1] if isinstance(result, tuple) else result.get('start_time')
                        db_end_str = result[2] if isinstance(result, tuple) else result.get('end_time')

                        if db_start_str and db_end_str:
                            try:
                                db_start = pd.to_datetime(db_start_str)
                                db_end = pd.to_datetime(db_end_str)

                                # Calculate overlap duration
                                overlap_duration = TaskManagementService._calculate_overlap_duration(
                                    db_start, db_end, completed_start, completed_end
                                )

                                if overlap_duration > best_overlap_duration:
                                    best_overlap_duration = overlap_duration
                                    best_match = result

                            except Exception as e:
                                logger.debug(f"Error parsing times for overlap calculation: {e}")
                                continue

                    if best_match and best_overlap_duration > timedelta(0):
                        # Update the best matching ongoing task
                        best_id = best_match[0] if isinstance(best_match, tuple) else best_match.get('id')
                        TaskManagementService._update_record_to_completed(table, best_id, completed_task)
                        logger.debug(f"✅ Updated best matching ongoing task {task_id} to completed (overlap: {best_overlap_duration})")
                        continue

                # If no task_id matches found or no good overlaps, try task_name overlap match
                overlap_query = f"""
                    SELECT id, start_time, end_time FROM {table.table_name}
                    WHERE robot_sn = '{robot_sn}'
                    AND task_name = '{task_name}'
                    AND is_report = 0
                    ORDER BY start_time DESC
                """

                overlap_results = table.query_data(overlap_query)

                # Find best overlap by task_name
                best_match = None
                best_overlap_duration = timedelta(0)

                for result in overlap_results:
                    record_id = result[0] if isinstance(result, tuple) else result.get('id')
                    db_start_str = result[1] if isinstance(result, tuple) else result.get('start_time')
                    db_end_str = result[2] if isinstance(result, tuple) else result.get('end_time')

                    if db_start_str and db_end_str:
                        try:
                            db_start = pd.to_datetime(db_start_str)
                            db_end = pd.to_datetime(db_end_str)

                            # Calculate overlap duration with tolerance
                            overlap_duration = TaskManagementService._calculate_overlap_duration_with_tolerance(
                                db_start, db_end, completed_start, completed_end
                            )

                            if overlap_duration > best_overlap_duration:
                                best_overlap_duration = overlap_duration
                                best_match = result

                        except:
                            continue

                if best_match and best_overlap_duration > timedelta(0):
                    # Update the best matching ongoing task by task_name
                    best_id = best_match[0] if isinstance(best_match, tuple) else best_match.get('id')
                    TaskManagementService._update_record_to_completed(table, best_id, completed_task)
                    logger.debug(f"✅ Updated best matching ongoing task (by name) to completed (overlap: {best_overlap_duration})")

            except Exception as e:
                logger.warning(f"⚠️ Error updating ongoing task for {robot_sn}: {e}")

    @staticmethod
    def _calculate_overlap_duration(ongoing_start: datetime, ongoing_end: datetime,
                                  completed_start: datetime, completed_end: datetime) -> timedelta:
        """Calculate the actual overlap duration between two time ranges."""
        try:
            # Find the overlap period
            overlap_start = max(ongoing_start, completed_start)
            overlap_end = min(ongoing_end, completed_end)

            # If overlap_start <= overlap_end, there's an overlap
            if overlap_start <= overlap_end:
                return overlap_end - overlap_start
            else:
                return timedelta(0)
        except:
            return timedelta(0)

    @staticmethod
    def _calculate_overlap_duration_with_tolerance(ongoing_start: datetime, ongoing_end: datetime,
                                                 completed_start: datetime, completed_end: datetime) -> timedelta:
        """Calculate overlap duration with tolerance for time estimation differences."""
        try:
            tolerance = timedelta(minutes=15)

            # Expand ongoing timeframe by tolerance
            ongoing_start_exp = ongoing_start - tolerance
            ongoing_end_exp = ongoing_end + tolerance

            # Calculate overlap
            overlap_start = max(ongoing_start_exp, completed_start)
            overlap_end = min(ongoing_end_exp, completed_end)

            if overlap_start <= overlap_end:
                return overlap_end - overlap_start
            else:
                return timedelta(0)
        except:
            return timedelta(0)

    @staticmethod
    def _update_record_to_completed(table: RDSTable, record_id: int, completed_task: dict):
        """Update ongoing task record to completed status."""
        try:
            updates = {
                'is_report': '1',
                'end_time': str(completed_task['end_time']),
                'progress': '100',
                'status': str(completed_task['status']),
                'map_url': str(completed_task.get('map_url', '')),
                'actual_area': str(completed_task['actual_area']),
                'efficiency': str(completed_task['efficiency']),
                'start_time': str(completed_task['start_time'])  # Update with actual start time
            }

            for field, value in updates.items():
                table.update_field_by_filters(field, value, {'id': record_id})

        except Exception as e:
            logger.error(f"❌ Error updating record {record_id}: {e}")

    @staticmethod
    def _times_overlap(ongoing_start: datetime, ongoing_end: datetime,
                      completed_start: datetime, completed_end: datetime) -> bool:
        """Check if ongoing and completed task times overlap with tolerance."""
        tolerance = timedelta(minutes=15)

        # Expand ongoing timeframe
        ongoing_start_exp = ongoing_start - tolerance
        ongoing_end_exp = ongoing_end + tolerance

        # Check overlap
        return max(ongoing_start_exp, completed_start) <= min(ongoing_end_exp, completed_end)