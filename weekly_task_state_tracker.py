import os
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from sprint_dates import get_current_sprint_dates

class WeeklyTaskStateTracker:
    def __init__(self):
        load_dotenv()
        self.pat = os.getenv('AZURE_DEVOPS_PAT')
        if not self.pat:
            raise ValueError("AZURE_DEVOPS_PAT not found in .env file")
        
        # Create authorization header
        encoded_pat = base64.b64encode(f':{self.pat}'.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_pat}',
            'Content-Type': 'application/json'
        }
        
        # Azure DevOps configuration
        self.organization = 'EvidaDevops'
        self.project = 'ETS2'
        self.tasks_query_id = '197b9a9b-22fa-4cfe-a7d9-10f4c5d17612'
    
    def get_weekly_buckets(self, start_date, end_date, include_future=False):
        """Generate weekly buckets from sprint start to end
        
        Args:
            start_date: Sprint start date (YYYY-MM-DD)
            end_date: Sprint end date (YYYY-MM-DD)
            include_future: If True, include all weeks until sprint end, otherwise stop at current week
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        now = datetime.now()
        
        buckets = []
        current = start
        
        while current <= end:
            # Get ISO calendar week number for the current date
            year, week_num, weekday = current.isocalendar()
            
            # Calculate the Monday of this ISO week (start of ISO week)
            week_start = current - timedelta(days=weekday - 1)
            # Calculate the Sunday of this ISO week (end of ISO week)
            week_end = week_start + timedelta(days=6)
            
            # Constrain to sprint boundaries
            actual_start = max(week_start, start)
            actual_end = min(week_end, end)
            
            # Stop at current week if not including future weeks
            if not include_future and week_start > now:
                break
            
            # Check if we haven't already added this week
            if not buckets or buckets[-1]['week'] != week_num:
                buckets.append({
                    'week': week_num,
                    'year': year,
                    'start': actual_start.strftime('%Y-%m-%d'),
                    'end': actual_end.strftime('%Y-%m-%d'),
                    'start_dt': actual_start,
                    'end_dt': actual_end,
                    'is_future': week_start > now
                })
            
            # Move to the next week
            current = week_end + timedelta(days=1)
        
        return buckets
    
    def get_task_ids(self):
        """Get all task IDs from the query"""
        wiql_url = f'https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/wiql/{self.tasks_query_id}'
        
        response = requests.get(wiql_url, headers=self.headers, params={'api-version': '6.0'})
        response.raise_for_status()
        results = response.json()
        
        work_items = results.get('workItems', [])
        return [item['id'] for item in work_items]
    
    def get_task_updates(self, task_id):
        """Get all updates/revisions for a specific task"""
        updates_url = f'https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workItems/{task_id}/updates'
        params = {'api-version': '7.0'}
        
        response = requests.get(updates_url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json().get('value', [])
    
    def get_task_info(self, task_id):
        """Get basic task information"""
        task_url = f'https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems/{task_id}'
        params = {'api-version': '7.0'}
        
        response = requests.get(task_url, headers=self.headers, params=params)
        response.raise_for_status()
        
        task_data = response.json()
        fields = task_data.get('fields', {})
        
        return {
            'id': task_id,
            'title': fields.get('System.Title', 'No title'),
            'current_state': fields.get('System.State', 'Unknown')
        }
    
    def get_tasks_baseline(self, task_ids):
        """Get current state of all tasks (baseline) - optimized batch fetch"""
        if not task_ids:
            return {}
        
        baseline = {}
        
        # Batch fetch all task details in a single API call
        details_url = f'https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems'
        details_params = {
            'ids': ','.join([str(id) for id in task_ids]),
            'api-version': '7.0',
            'fields': 'System.Title,System.State'
        }
        
        try:
            response = requests.get(details_url, headers=self.headers, params=details_params)
            response.raise_for_status()
            result = response.json()
            
            work_items = result.get('value', [])
            
            for item in work_items:
                task_id = item['id']
                fields = item.get('fields', {})
                baseline[task_id] = {
                    'title': fields.get('System.Title', 'No title'),
                    'state': fields.get('System.State', 'Unknown')
                }
            
            print(f"Baseline fetched for {len(baseline)} tasks in a single batch API call")
            
        except Exception as e:
            print(f"Error fetching baseline in batch: {str(e)}", flush=True)
            # Fallback: return empty baseline or handle error
            baseline = {}
        
        return baseline
    
    def get_state_at_week_end(self, updates, week_end_dt):
        """Determine the state of a task at the end of a specific week"""
        # Sort updates by revisedDate
        sorted_updates = sorted(updates, key=lambda x: x.get('revisedDate', ''))
        
        current_state = None
        
        # Set the week end to end of day (23:59:59)
        week_end_eod = week_end_dt.replace(hour=23, minute=59, second=59)
        
        for update in sorted_updates:
            revised_date_str = update.get('revisedDate', '')
            if not revised_date_str:
                continue
            
            # Parse the revised date
            revised_date = datetime.fromisoformat(revised_date_str.replace('Z', '+00:00'))
            revised_date_naive = revised_date.replace(tzinfo=None)
            
            # Handle far-future dates (like 9999-01-01) as current time
            # This appears to be a placeholder used by Azure DevOps for certain updates
            if revised_date_naive.year > 2100:
                revised_date_naive = datetime.now()
            
            # If this update happened after the week end, stop
            if revised_date_naive > week_end_eod:
                break
            
            # Check if state changed in this update
            fields = update.get('fields', {})
            if 'System.State' in fields:
                state_info = fields['System.State']
                if 'newValue' in state_info:
                    current_state = state_info['newValue']
                elif 'oldValue' not in state_info and update.get('rev') == 1:
                    # First revision - get the initial state
                    current_state = state_info.get('newValue') or state_info.get('oldValue')
        
        return current_state
    
    def process_single_task(self, task_id, weekly_buckets, baseline, idx, total):
        """Process a single task and return its weekly states"""
        print(f"Processing task {idx}/{total}: {task_id}", flush=True)
        
        try:
            # Get baseline state and title
            baseline_state = baseline[task_id]['state']
            baseline_title = baseline[task_id]['title']
            
            # Get all updates for this task
            updates = self.get_task_updates(task_id)
            
            # For each week, determine the state
            task_weekly_states = {}
            for bucket in weekly_buckets:
                week_num = bucket['week']
                year = bucket['year']
                
                # Start with baseline state
                state = baseline_state
                
                # For the current week, use today's date instead of week end
                now = datetime.now()
                if bucket['end_dt'] >= now.replace(hour=0, minute=0, second=0, microsecond=0):
                    # Current or future week - use current date/time as cutoff
                    cutoff_date = now
                else:
                    # Past week - use end of week
                    cutoff_date = bucket['end_dt']
                
                # Check if state was different at week end
                historical_state = self.get_state_at_week_end(updates, cutoff_date)
                if historical_state:
                    state = historical_state
                
                # Always include task in weekly bucket (with baseline or historical state)
                task_weekly_states[f"week_{year}_{week_num}"] = {
                    'title': baseline_title,
                    'state': state
                }
            
            return (task_id, task_weekly_states)
        
        except Exception as e:
            print(f"  Error processing task {task_id}: {str(e)}", flush=True)
            return (task_id, {})
    
    def track_weekly_states(self):
        """Track task states on a weekly basis"""
        print("Fetching current sprint dates...")
        sprint_info = get_current_sprint_dates(self.pat)
        
        if not sprint_info:
            print("No current sprint found!")
            return None
        
        print(f"\nSprint: {sprint_info['name']}")
        print(f"Start: {sprint_info['start']}")
        print(f"End: {sprint_info['end']}\n")
        
        # Generate weekly buckets - include all weeks through the end of all sprints
        weekly_buckets = self.get_weekly_buckets(sprint_info['start'], sprint_info['end'], include_future=True)
        print(f"Tracking {len(weekly_buckets)} weeks...\n")
        
        # Get all task IDs
        print("Fetching task IDs...")
        task_ids = self.get_task_ids()
        print(f"Found {len(task_ids)} tasks\n")
        
        # Get baseline (current state of all tasks)
        print("Fetching baseline task states...")
        baseline = self.get_tasks_baseline(task_ids)
        print(f"Baseline fetched for {len(baseline)} tasks\n")
        
        # Track states for each task using multithreading
        weekly_task_states = defaultdict(lambda: defaultdict(dict))
        
        print("Processing tasks with 10 concurrent threads...\n")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self.process_single_task, task_id, weekly_buckets, baseline, idx, len(task_ids)): task_id
                for idx, task_id in enumerate(task_ids, 1)
            }
            
            # Process completed tasks
            for future in as_completed(future_to_task):
                task_id, task_weekly_states = future.result()
                
                # Merge results into weekly_task_states
                for week_key, task_data in task_weekly_states.items():
                    weekly_task_states[week_key][task_id] = task_data
        
        return {
            'sprint': sprint_info,
            'weekly_buckets': weekly_buckets,
            'weekly_states': dict(weekly_task_states)
        }
    
    def get_weekly_task_states(self, include_future_weeks=True):
        """
        Get weekly task states in a clean format.
        Returns a list of weeks with ISO week numbers and tasks with their states.
        
        Args:
            include_future_weeks: If True, include future weeks in the sprint with no task data
        
        Returns:
            list: List of dictionaries with structure:
                [
                    {
                        'week': int (ISO week number),
                        'year': int,
                        'start_date': str (YYYY-MM-DD),
                        'end_date': str (YYYY-MM-DD),
                        'is_future': bool,
                        'tasks': [
                            {
                                'id': int,
                                'title': str,
                                'state': str
                            },
                            ...
                        ]
                    },
                    ...
                ]
        """
        results = self.track_weekly_states()
        
        if not results:
            return []
        
        sprint_info = results['sprint']
        weekly_states = results['weekly_states']
        
        # Get all weekly buckets including future weeks if requested
        all_weekly_buckets = self.get_weekly_buckets(
            sprint_info['start'], 
            sprint_info['end'],
            include_future=include_future_weeks
        )
        
        output = []
        
        for bucket in all_weekly_buckets:
            week_key = f"week_{bucket['year']}_{bucket['week']}"
            week_data = {
                'week': bucket['week'],
                'year': bucket['year'],
                'start_date': bucket['start'],
                'end_date': bucket['end'],
                'is_future': bucket.get('is_future', False),
                'tasks': []
            }
            
            # Only add tasks if this is not a future week
            if not bucket.get('is_future', False) and week_key in weekly_states:
                for task_id, task_info in weekly_states[week_key].items():
                    week_data['tasks'].append({
                        'id': task_id,
                        'title': task_info['title'],
                        'state': task_info['state']
                    })
                
                # Sort tasks by ID
                week_data['tasks'].sort(key=lambda x: x['id'])
            
            output.append(week_data)
        
        return output

def main():
    tracker = WeeklyTaskStateTracker()
    
    # Get weekly task states
    weekly_data = tracker.get_weekly_task_states()
    
    # Print the contents
    print("="*80)
    print("WEEKLY TASK STATES")
    print("="*80)
    
    for week in weekly_data:
        print(f"\nWeek {week['week']} ({week['year']}): {week['start_date']} to {week['end_date']}")
        print("-" * 80)
        
        if week['tasks']:
            # Group tasks by state
            by_state = {}
            for task in week['tasks']:
                state = task['state']
                if state not in by_state:
                    by_state[state] = []
                by_state[state].append(task)
            
            # Print tasks grouped by state
            for state in sorted(by_state.keys()):
                print(f"\n  [{state}] ({len(by_state[state])} tasks)")
                for task in by_state[state]:
                    print(f"    • Task {task['id']}: {task['title']}")
        else:
            print("  No tasks tracked in this week")

if __name__ == '__main__':
    main()
