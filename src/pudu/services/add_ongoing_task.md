Robot Task Tracking Logic and SQL Guide

1. Problem Context
	•	Completed tasks: These come from reports with a fixed start_time. They represent the authoritative records of what happened.
	•	In-progress tasks: These are created when a robot is currently performing a task. They do not have a reliable start_time from the external source (only estimates), so they cannot use start_time in uniqueness constraints.
	•	Requirement: A robot can only have one ongoing task at a time.

2. Schema Adjustments
	•	Add a new column to mark ongoing tasks:

ALTER TABLE foxx_irvine_office_test.mnt_robots_task
ADD COLUMN is_ongoing INT NOT NULL DEFAULT 0 AFTER task_name;

	•	Unique constraints:
	•	For completed tasks (existing): (task_name, robot_sn, start_time)
	•	For ongoing tasks (new): (robot_sn, is_ongoing) to ensure only one ongoing task per robot.

ALTER TABLE foxx_irvine_office_test.mnt_robots_task
ADD CONSTRAINT uq_robot_ongoing UNIQUE (robot_sn, is_ongoing);

3. State Machine

   [Idle]
     ↓ (API shows task started)
[Ongoing Task Created]
     ↓ (Robot still working, estimates updated)
[Ongoing Task Updated]
     ↓ (API shows robot idle, fetch reports)
     ├── No report found → Keep ongoing
     └── Matching report found → Insert completed task + Delete ongoing task
[Completed Task Stored]

4. SQL Operations

Insert an Ongoing Task

INSERT INTO foxx_irvine_office_test.mnt_robots_task
(task_id, robot_sn, task_name, is_ongoing, mode, sub_mode, `type`,
 vacuum_speed, vacuum_suction, wash_speed, wash_suction, wash_water,
 map_name, map_url, actual_area, plan_area, start_time, end_time,
 duration, efficiency, remaining_time, consumption, water_consumption,
 progress, status, create_time, update_time, tenant_id)
VALUES
('ONGOING_001', '811064412050012', 'ISA 1st floor wet', 1,
 'Scrubbing', 'Custom', 'Custom', 'Off', 'Off', 'Standard', 'Medium', 'Medium',
 '1#11#USF-ISA-1ST-FLOORV2', 'https://example.com/map.png',
 0, 0, NOW(), NULL, NULL, NULL, NULL, NULL, NULL, 0,
 'Task Ongoing', NOW(), NOW(), '000000');

Update an Ongoing Task (progress or estimates)

UPDATE foxx_irvine_office_test.mnt_robots_task
SET progress = 50,
    start_time = NOW()
WHERE robot_sn = '811064412050012'
  AND task_name = 'ISA 1st floor wet'
  AND is_ongoing = 1;

Resolve Ongoing Task → Completed

When the robot goes idle:
	1.	Fetch reports from external API.
	2.	For each report, check overlap with estimated task time range.
	3.	If overlap found, insert completed record:

INSERT INTO foxx_irvine_office_test.mnt_robots_task
(... all columns ... , is_ongoing)
VALUES
(... real report data ..., 0);

	4.	Delete the ongoing placeholder:

DELETE FROM foxx_irvine_office_test.mnt_robots_task
WHERE robot_sn = '811064412050012'
  AND task_name = 'ISA 1st floor wet'
  AND is_ongoing = 1;

Clean Up Stale Ongoing Tasks

If an ongoing task never gets resolved (robot crashed, data missing):

UPDATE foxx_irvine_office_test.mnt_robots_task
SET status = 'Abandoned'
WHERE is_ongoing = 1
  AND update_time < NOW() - INTERVAL 24 HOUR;

5. Benefits of This Design
	•	Keeps completed tasks authoritative with fixed start_time.
	•	Prevents duplication by ensuring only one ongoing task per robot.
	•	Allows smooth transition from in-progress to completed tasks.
	•	Provides safety net for stale ongoing tasks.

⸻

✅ This approach ensures a clean, consistent task history while still capturing real-time in-progress state.