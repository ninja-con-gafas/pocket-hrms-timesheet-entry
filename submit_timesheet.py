#!/usr/bin/env python3

"""
Timesheet Submission Tool
Reads timesheet entries from CSV and submits to PocketHRMS
"""

import csv
import json
import sys
import requests
from datetime import datetime

DEFAULTS = {
    'ProjectTaskId': '2',
    'ProjectTaskName': 'MyTask',
    'InHours': '0:0',
    'InTime': '0',
    'OutHours': '0:0',
    'ClientName': 'My Client',
    'SubProjectName': '',
    'IsBillableEntry': False,
    'Status': '0',
    'PageName': 'ProjectManagement',
    'EntryFrom': 'Web',
    'Module': 'Project'
}

REQUEST_DEFAULTS = {
    'IsClientMandatory': 'Description,Entry Date,Task Date,Project Name,Start Time,End Time,Client',
    'WeekoffVal': 'Yes',
    'drpSubMaster': '',
    'Task': '2',
    'drpclientName': 'My Client',
    'TotalHours': '08',
    'TotalMin': '00',
    'PageName': '',
    'Attachedfile': 'application/octet-stream'
}

REQUIRED_TOTAL_MINUTES = 480

def load_project_mappings():
    try:
        with open('projects_mapping.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Error: projects_mapping.json not found.")
        print("This file is required for project name lookup.")
        sys.exit(1)

def load_auth_credentials():
    from session import cookies, headers
    return cookies, headers

def convert_date_format(date_str):
    try:
        date_obj = datetime.strptime(date_str.strip(), '%d/%m/%Y')
        return date_obj.strftime('%m/%d/%Y')
    except ValueError as error:
        print(f"Error: Invalid date format '{date_str}'. Expected DD/MM/YYYY: {error}")
        sys.exit(1)

def convert_date_format_reverse(date_str):
    try:
        date_obj = datetime.strptime(date_str.strip(), '%m/%d/%Y')
        return date_obj.strftime('%d/%m/%Y')
    except ValueError:
        return date_str

def load_csv_entries(csv_file):
    entries = []

    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                # Validate mandatory fields
                mandatory_fields = ['FromDate', 'ToDate', 'ProjectId', 'Description', 'OutTime']
                missing_fields = [field for field in mandatory_fields if not row.get(field, '').strip()]

                if missing_fields:
                    print(f"Error: Row {row_num} missing mandatory fields: {', '.join(missing_fields)}")
                    sys.exit(1)

                # Build entry with defaults
                entry = {
                    'FromDate': convert_date_format(row['FromDate']),
                    'ToDate': convert_date_format(row['ToDate']),
                    'ProjectId': row['ProjectId'].strip(),
                    'ProjectName': '',  # Will be filled later
                    'Description': row['Description'].strip(),
                    'OutTime': row['OutTime'].strip(),
                }

                # Add optional fields with defaults
                for field, default_value in DEFAULTS.items():
                    if row.get(field, '').strip():
                        # User provided a value
                        value = row[field].strip()
                        # Convert to boolean for IsBillableEntry
                        if field == 'IsBillableEntry':
                            entry[field] = value.lower() in ('true', 'yes', '1')
                        else:
                            entry[field] = value
                    else:
                        # Use default
                        entry[field] = default_value

                entries.append(entry)

        return entries

    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found.")
        sys.exit(1)
    except Exception as error:
        print(f"Error reading CSV file: {error}")
        sys.exit(1)

def validate_project_ids(entries, project_mappings):
    for i, entry in enumerate(entries, start=1):
        project_id = entry['ProjectId']

        if project_id not in project_mappings:
            print(f"Error: Entry {i} has invalid ProjectId '{project_id}'")
            print("Please check projects_list.csv for valid project IDs")
            sys.exit(1)

        # Auto-fill project name
        entry['ProjectName'] = project_mappings[project_id]
        print(f"Entry {i}: ProjectId {project_id} → '{entry['ProjectName']}'")

def validate_total_time(entries):
    # Group entries by date
    date_groups = {}
    for entry in entries:
        date_key = entry['FromDate']
        if date_key not in date_groups:
            date_groups[date_key] = []
        date_groups[date_key].append(entry)

    # Validate each date group
    for date, date_entries in date_groups.items():
        total_minutes = sum(int(entry['OutTime']) for entry in date_entries)

        if total_minutes != REQUIRED_TOTAL_MINUTES:
            print(f"\nError: Total OutTime validation failed for {date}!")
            print(f"  Required: {REQUIRED_TOTAL_MINUTES} minutes (8 hours)")
            print(f"  Actual:   {total_minutes} minutes ({total_minutes/60:.2f} hours)")
            print(f"  Difference: {total_minutes - REQUIRED_TOTAL_MINUTES} minutes")
            print("\nEntries for this date:")
            for entry in date_entries:
                out_time = int(entry['OutTime'])
                print(f"    {out_time} min ({out_time/60:.1f}h): {entry['Description'][:50]}")
            sys.exit(1)

def prepare_request_data(entries):
    # Group entries by date
    date_groups = {}
    for entry in entries:
        date_key = entry['FromDate']
        if date_key not in date_groups:
            date_groups[date_key] = []
        date_groups[date_key].append(entry)

    # Prepare requests for each date
    requests_data = []

    for date, date_entries in date_groups.items():
        # Calculate total time
        total_minutes = sum(int(entry['OutTime']) for entry in date_entries)
        total_hours = total_minutes // 60
        total_mins = total_minutes % 60

        # Get first entry for some fields
        first_entry = date_entries[0]

        # Prepare files dictionary
        # Format: field_name: (filename, fileobj, content_type) or (filename, fileobj) or just value
        files = {
            'hdnData': (None, json.dumps(date_entries)),
            'IsClientMandatory': (None, REQUEST_DEFAULTS['IsClientMandatory']),
            'WeekoffVal': (None, REQUEST_DEFAULTS['WeekoffVal']),
            'ToDate': (None, convert_date_format_reverse(first_entry['ToDate'])),
            'projectCode': (None, first_entry['ProjectId']),
            'ProjectName': (None, first_entry['ProjectId']),
            'drpSubMaster': (None, REQUEST_DEFAULTS['drpSubMaster']),
            'Task': (None, REQUEST_DEFAULTS['Task']),
            'drpclientName': (None, REQUEST_DEFAULTS['drpclientName']),
            'TotalHours': (None, f"{total_hours:02d}"),
            'TotalMin': (None, f"{total_mins:02d}"),
            'Description': (None, first_entry['Description']),
            'PageName': (None, REQUEST_DEFAULTS['PageName']),
            'Attachedfile': REQUEST_DEFAULTS['Attachedfile']
        }

        requests_data.append({
            'date': date,
            'files': files,
            'entry_count': len(date_entries),
            'total_time': total_minutes
        })

    return requests_data

def submit_timesheet(files, cookies, headers):
    url = 'https://ess.pockethrms.com/Employee/Profile/TimeEntryNew'

    try:
        response = requests.post(url, cookies=cookies, headers=headers, files=files)
        return response
    except requests.RequestException as error:
        print(f"Error: Failed to submit timesheet - {error}")
        return None

def display_summary(entries):
    # Group by date
    date_groups = {}
    for entry in entries:
        date_key = entry['FromDate']
        if date_key not in date_groups:
            date_groups[date_key] = []
        date_groups[date_key].append(entry)

    for date, date_entries in date_groups.items():
        total_minutes = sum(int(entry['OutTime']) for entry in date_entries)
        total_hours = total_minutes // 60
        total_mins = total_minutes % 60

        print(f"\nDate: {convert_date_format_reverse(date)}")
        print(f"Total entries: {len(date_entries)}")
        print(f"Total time: {total_hours}h {total_mins}m ({total_minutes} minutes)")
        print(f"Status: {'VALID' if total_minutes == REQUIRED_TOTAL_MINUTES else 'INVALID'}")
        print("-" * 80)

        for i, entry in enumerate(date_entries, 1):
            out_time = int(entry['OutTime'])
            hours = out_time // 60
            mins = out_time % 60

            print(f"\n  Entry {i}:")
            print(f"    Project: {entry['ProjectName']} (ID: {entry['ProjectId']})")
            print(f"    Task: {entry['ProjectTaskName']} (ID: {entry['ProjectTaskId']})")
            print(f"    Time: {hours}h {mins}m ({out_time} minutes)")
            print(f"    Description: {entry['Description'][:70]}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python submit_timesheet.py timesheet.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    # Load project mappings
    print("\n[1/6] Loading project mappings")
    project_mappings = load_project_mappings()
    print(f"      Loaded {len(project_mappings)} projects")

    # Load CSV entries
    print(f"\n[2/6] Loading entries from CSV: {csv_file}")
    entries = load_csv_entries(csv_file)
    print(f"      Loaded {len(entries)} entries")

    # Validate project IDs and fill project names
    print("\n[3/6] Validating project IDs and filling project names")
    validate_project_ids(entries, project_mappings)
    print("      All project IDs valid")

    # Validate total time
    print("\n[4/6] Validating total time (must equal 480 minutes per date)")
    validate_total_time(entries)
    print("      Time validation passed")

    # Display summary
    print("\n[5/6] Preparing submission")
    display_summary(entries)

    # Load authentication
    print(f"[6/6] Loading authentication")
    cookies, headers = load_auth_credentials()

    # Check if auth is configured
    if not cookies or not headers:
        print("\nWARNING: Authentication not configured!")
        print("  Please update auth.json with your actual session cookies and tokens.")
        print("\nValidation completed successfully. Configure auth.json to submit.")
        return

    print("      Authentication loaded")

    # Prepare requests
    requests_data = prepare_request_data(entries)

    for i, req_data in enumerate(requests_data, 1):
        date_display = convert_date_format_reverse(req_data['date'])
        print(f"Submitting entries for {date_display} ({req_data['entry_count']} entries, {req_data['total_time']} minutes)")

        response = submit_timesheet(req_data['files'], cookies, headers)

        if response.status_code == 200:
            print(f"  SUCCESS: Entries submitted (Status {response.status_code})")
        else:
            print(f"  FAILED: Submission failed (Status {response.status_code})")
            print(f"  Response: {response.text[:200]}")
            
if __name__ == "__main__":
    main()
