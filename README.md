# Timesheet Submission Tool

A CSV-based automation tool for submitting timesheet entries to PocketHRMS, including validation, automatic date conversion, project name autofill, and grouped submission by date.

---

## Quick Start

### 1. Prepare Your Files

**Required files:**
- `timesheet.csv`: Your timesheet entries (create from [template](timesheet_template.csv))
- `session.py`: Contains your session `cookies` and request `headers` for authentication.
- `projects_mapping.json`: Refer for the `ProjectId` associated with the `ProjectName`.

### 2. Fill Your Timesheet

Create `timesheet.csv` using the [template](timesheet_template.csv) with your entries.


These columns must be present and filled:

| Column | Format | Example | Description |
|--------|--------|---------|-------------|
| FromDate | DD/MM/YYYY | 23/11/2025 | Entry start date |
| ToDate | DD/MM/YYYY | 23/11/2025 | Entry end date |
| ProjectId | String | 148 | `ProjectId` (Refer [projects_mapping.json](projects_mapping.json) for the `ProjectId`.) |
| Description | String | Description of your task. | Work description |
| OutTime | Integer | 480 | Duration in minutes |

These columns have default values if not provided:

| Column | Default Value |
|--------|---------------|
| ProjectTaskId | 2 |
| ProjectTaskName | MyTask |
| InHours | 0:0 |
| InTime | 0 |
| OutHours | 0:0 |
| ClientName | My Client |
| SubProjectName | (empty) |
| IsBillableEntry | false |
| Status | 0 |
| PageName | ProjectManagement |
| EntryFrom | Web |
| Module | Project |


### 3. Configure Authentication

Create a `session.py` file with two variables:

```python
cookies = {
    '_gcl_au': 'your_value',
    'XNPocketToken': 'your_token',
    # ... other cookies ...
}

headers = {
    'accept': '*/*',
    'referer': 'https://ess.pockethrms.com/ProjectManagement/Transaction/ProjectManagementRequest?Menu=TimesheetEntryNew',
    'user-agent': 'Mozilla/5.0 ...',
    # ... other headers ...
}
```

### 4. Submit

```bash
python submit_timesheet.py timesheet.csv
```
---

## Templates

### Single Entry For A Day

|FromDate|ToDate|ProjectId|Description|OutTime|ProjectTaskId|ProjectTaskName|InHours|InTime|OutHours|ClientName|SubProjectName|IsBillableEntry|Status|PageName|EntryFrom|Module|
|--------|------|---------|-----------|-------|-------------|---------------|-------|------|--------|----------|--------------|---------------|------|--------|---------|------|
|23/11/2025|23/11/2025|148|"Description of your task."|480|2|MyTask|0:0|0|0:0|My Client| |false|0|ProjectManagement|Web|Project|

### Multiple Entries For A Day

|FromDate|ToDate|ProjectId|Description|OutTime|ProjectTaskId|ProjectTaskName|InHours|InTime|OutHours|ClientName|SubProjectName|IsBillableEntry|Status|PageName|EntryFrom|Module|
|--------|------|---------|-----------|-------|-------------|---------------|-------|------|--------|----------|--------------|---------------|------|--------|---------|------|
|23/11/2025|23/11/2025|148|Description of your task.|300|  | | | | | | | | | | | |
|23/11/2025|23/11/2025|148|Description of your task.|180| | | | | | | | | | | | |

Note: Total OutTime = 300 + 180 = 480 minutes

---

## Validation Rules

1. Mandatory Fields Check: All entries must have: `FromDate`, `ToDate`, `ProjectId`, `Description`, `OutTime`
2. Date Format Validation: All dates must be in DD/MM/YYYY format.
3. `ProjectId` Validation: ProjectId must exist in `projects_mapping.json`.
4. Total Time Validation: Entries for the same date must total exactly 480 minutes (8 hours).
5. Auto-Corrections: 
- Project names are auto-filled from ProjectId
- Missing optional fields use defaults
- Date formats are auto-converted

---
