# 🛰️ Robot Coordinate Logging System

This document outlines a system for logging robot coordinate traces using fixed-length JSON arrays in PostgreSQL. This approach maintains a continuous trace by storing a fixed number of the most recent coordinates for each robot, ensuring complete path continuity without database overflow.

---

## 1. Database Schema

The robot traces are stored in the `mnt_robot_trace_json` table. Each row represents a single robot with its complete coordinate history maintained as a rolling buffer of fixed size.

**Table:** `foxx_irvine_office_test.mnt_robot_trace_json`

| Column                 | Type          | Description                                                           |
|------------------------|---------------|-----------------------------------------------------------------------|
| `robot_sn`            | `VARCHAR(100)`| Primary key - Serial number or unique identifier of the robot.       |
| `max_coordinates`     | `INTEGER`     | Maximum number of coordinates to maintain (default: 1000).           |
| `current_count`       | `INTEGER`     | Current number of coordinates stored.                                 |
| `first_coordinate_time`| `TIMESTAMP`   | Timestamp of the **oldest** coordinate in the array.                |
| `last_coordinate_time` | `TIMESTAMP`   | Timestamp of the **newest** coordinate in the array.                |
| `last_updated`        | `TIMESTAMP`   | When this robot's data was last modified.                           |
| `coordinates`         | `JSONB`       | A JSON array containing the most recent coordinates `(x, y, z, t)`.  |

```sql
CREATE TABLE foxx_irvine_office_test.mnt_robot_trace_json (
  robot_sn VARCHAR(100) PRIMARY KEY,
  max_coordinates INTEGER NOT NULL DEFAULT 1000,
  current_count INTEGER NOT NULL DEFAULT 0,
  first_coordinate_time TIMESTAMP,
  last_coordinate_time TIMESTAMP,
  last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
  coordinates JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- Constraints to ensure data integrity
  CONSTRAINT check_coordinate_count CHECK (current_count <= max_coordinates),
  CONSTRAINT check_coordinate_array_size CHECK (jsonb_array_length(coordinates) = current_count)
);

-- Indexes for performance
CREATE INDEX idx_robot_trace_time_range ON foxx_irvine_office_test.mnt_robot_trace_json(first_coordinate_time, last_coordinate_time);
CREATE INDEX idx_robot_trace_updated ON foxx_irvine_office_test.mnt_robot_trace_json(last_updated);

-- Optional: GIN index for coordinate data queries
CREATE INDEX idx_robot_coordinates_gin ON foxx_irvine_office_test.mnt_robot_trace_json USING gin (coordinates);
```

---

## 2. Fixed-Length Rolling Buffer Logic

To maintain continuous traces while preventing database overflow, each robot maintains exactly `max_coordinates` (default: 1000) of the most recent coordinate points. When new coordinates arrive:

1. **Buffer Management:** Coordinates are still buffered in memory before database writes for efficiency.
2. **Rolling Window:** When the coordinate limit is reached, the oldest coordinates are automatically removed.
3. **Continuity Guarantee:** The system always maintains the most recent N coordinates, ensuring trace continuity even during long idle periods.

**Key Parameters:**
- `MAX_COORDINATES_PER_ROBOT = 1000` - Maximum coordinates stored per robot
- `MAX_POINTS = 20` - Buffer size before database write
- `MAX_TIME_GAP = 60 seconds` - Time gap before forced buffer flush

---

## 3. Data Format

The `coordinates` field stores a JSON array where each object contains the robot's position and timestamp. The array is maintained as a rolling buffer with the most recent coordinates.

**Example JSON for a `coordinates` field:**
```json
[
  {"x": 1.1, "y": 2.1, "z": 0.0, "t": "2025-07-07T10:00:00"},
  {"x": 1.2, "y": 2.2, "z": 0.0, "t": "2025-07-07T10:00:05"},
  {"x": 1.3, "y": 2.3, "z": 0.0, "t": "2025-07-07T10:00:10"}
]
```

**Note:** The array is chronologically ordered with the oldest coordinate first and newest coordinate last.

---

## 4. System Operations

### Data Ingestion (Python Implementation)

This Python implementation demonstrates the buffering logic with fixed-length rolling buffer management.

```python
import psycopg2
import json
from datetime import datetime, timedelta

# Configuration
MAX_COORDINATES_PER_ROBOT = 1000
MAX_POINTS = 20
MAX_TIME_GAP = timedelta(seconds=60)

# In-memory buffer for a single robot
trace_buffer = {
    "robot_sn": "RBT-001",
    "start_time": None,
    "last_time": None,
    "coordinates": []
}

def add_coordinate_to_robot(robot_sn, coord):
    """Add coordinate to robot maintaining fixed count limit."""
    coord_time = datetime.fromisoformat(coord["t"])

    # Get current coordinates for this robot
    cur.execute("""
        SELECT coordinates, current_count FROM foxx_irvine_office_test.mnt_robot_trace_json
        WHERE robot_sn = %s;
    """, (robot_sn,))

    result = cur.fetchone()
    if result:
        current_coords = json.loads(result[0])
        current_count = result[1]
    else:
        current_coords = []
        current_count = 0

    # Add new coordinate
    current_coords.append(coord)

    # Remove oldest coordinates if exceeding limit
    if len(current_coords) > MAX_COORDINATES_PER_ROBOT:
        current_coords = current_coords[-MAX_COORDINATES_PER_ROBOT:]

    new_count = len(current_coords)
    first_time = datetime.fromisoformat(current_coords[0]["t"]) if current_coords else None
    last_time = datetime.fromisoformat(current_coords[-1]["t"]) if current_coords else None

    # Update or insert robot data
    cur.execute("""
        INSERT INTO foxx_irvine_office_test.mnt_robot_trace_json
        (robot_sn, max_coordinates, current_count, first_coordinate_time,
         last_coordinate_time, last_updated, coordinates)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (robot_sn) DO UPDATE SET
            current_count = EXCLUDED.current_count,
            first_coordinate_time = EXCLUDED.first_coordinate_time,
            last_coordinate_time = EXCLUDED.last_coordinate_time,
            last_updated = EXCLUDED.last_updated,
            coordinates = EXCLUDED.coordinates;
    """, (
        robot_sn, MAX_COORDINATES_PER_ROBOT, new_count,
        first_time, last_time, datetime.now(), json.dumps(current_coords)
    ))

    conn.commit()

def insert_trace_to_db(buffer):
    """Inserts the buffered trace segment with coordinate limit enforcement."""
    for coord in buffer["coordinates"]:
        add_coordinate_to_robot(buffer["robot_sn"], coord)

def on_new_coordinate(coord):
    """Handles an incoming coordinate point with buffering."""
    global trace_buffer
    now = datetime.fromisoformat(coord["t"])

    # Initialize buffer if it's the first point
    if trace_buffer["start_time"] is None:
        trace_buffer["start_time"] = now

    # Flush buffer if time gap is exceeded
    if (trace_buffer["last_time"] is not None and
        now - trace_buffer["last_time"] > MAX_TIME_GAP):
        insert_trace_to_db(trace_buffer)
        # Reset buffer for a new segment
        trace_buffer = {"robot_sn": coord["robot_sn"], "start_time": now, "last_time": None, "coordinates": []}

    # Add coordinate to buffer
    trace_buffer["coordinates"].append(coord)
    trace_buffer["last_time"] = now

    # Flush buffer if max points are reached
    if len(trace_buffer["coordinates"]) >= MAX_POINTS:
        insert_trace_to_db(trace_buffer)
        # Reset buffer
        trace_buffer = {"robot_sn": coord["robot_sn"], "start_time": None, "last_time": None, "coordinates": []}
```

### Data Retrieval (SQL Queries)

#### Get Complete Robot Path
```sql
-- Get all coordinates for a specific robot (already ordered)
SELECT coordinates AS full_path
FROM foxx_irvine_office_test.mnt_robot_trace_json
WHERE robot_sn = 'RBT-001';
```

#### Get Robot Path for Time Range
```sql
-- Get coordinates within a specific time range
SELECT jsonb_agg(elem ORDER BY (elem->>'t')::timestamp) AS filtered_path
FROM (
    SELECT jsonb_array_elements(coordinates) AS elem
    FROM foxx_irvine_office_test.mnt_robot_trace_json
    WHERE robot_sn = 'RBT-001'
      AND first_coordinate_time <= '2025-07-08 23:59:59'
      AND last_coordinate_time >= '2025-07-07 00:00:00'
) AS expanded_coords
WHERE (elem->>'t')::timestamp BETWEEN '2025-07-07 00:00:00' AND '2025-07-08 23:59:59';
```

#### Get Robot Status Summary
```sql
-- Get summary information for all robots
SELECT
    robot_sn,
    current_count,
    max_coordinates,
    first_coordinate_time,
    last_coordinate_time,
    EXTRACT(EPOCH FROM (last_coordinate_time - first_coordinate_time)) / 3600 AS trace_duration_hours,
    last_updated
FROM foxx_irvine_office_test.mnt_robot_trace_json
ORDER BY last_updated DESC;
```

#### Get Recent Robot Positions
```sql
-- Get the most recent position of each robot
SELECT
    robot_sn,
    coordinates->-1 AS latest_position,
    last_coordinate_time,
    current_count
FROM foxx_irvine_office_test.mnt_robot_trace_json
WHERE current_count > 0
ORDER BY last_coordinate_time DESC;
```

---

## 5. Advantages of Fixed-Length Approach

- **Guaranteed Continuity**: Always maintains the most recent N coordinates, ensuring complete trace continuity regardless of time gaps.
- **Predictable Storage**: Each robot uses exactly the same amount of storage, preventing database overflow.
- **No Data Loss Gaps**: Unlike time-based cleanup, this approach never creates discontinuous traces.
- **Efficient Queries**: Single row per robot enables fast retrieval of complete paths.
- **Automatic Management**: No external cleanup processes required - the system self-maintains.
- **Scalability**: Storage requirements scale linearly with the number of robots, not with time.

---

## 6. Configuration Guidelines

### Choosing `max_coordinates`
- **High-frequency robots** (1 coordinate/second): 1000 coordinates ≈ 16 minutes of trace
- **Medium-frequency robots** (1 coordinate/5 seconds): 1000 coordinates ≈ 1.4 hours of trace
- **Low-frequency robots** (1 coordinate/minute): 1000 coordinates ≈ 16 hours of trace

### Storage Considerations
- Each coordinate: ~50-80 bytes (depending on precision)
- 1000 coordinates per robot: ~50-80 KB per robot
- 100 robots: ~5-8 MB total storage

### Performance Tuning
- Increase `MAX_POINTS` (buffer size) to reduce database write frequency
- Adjust `max_coordinates` based on your trace length requirements
- Use GIN indexes for complex coordinate queries
- Consider partitioning by robot_sn for very large deployment