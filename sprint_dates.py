import requests
import base64
from datetime import datetime, timedelta


def get_all_iterations(pat):
    """
    Get all iterations for team Kvoteklubben with individual sprint details
    
    Args:
        pat: Personal Access Token for Azure DevOps
        
    Returns:
        list of dicts with keys: 'name', 'start', 'end' (dates in YYYY-MM-DD format)
        or None if no iterations found
    """
    # Azure DevOps configuration
    organization = 'EvidaDevops'
    project = 'ETS2'
    team = 'Kvoteklubben'
    
    # Create authorization header
    encoded_pat = base64.b64encode(f':{pat}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_pat}',
        'Content-Type': 'application/json'
    }
    
    # Get all iterations for the team (no timeframe filter)
    url = f'https://dev.azure.com/{organization}/{project}/{team}/_apis/work/teamsettings/iterations'
    params = {
        'api-version': '7.0'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        iterations_data = data.get('value', [])
        
        if not iterations_data:
            print("No iterations found for team Kvoteklubben")
            return None
        
        # Parse all iterations
        iterations = []
        for iteration in iterations_data:
            attributes = iteration.get('attributes', {})
            start_date_str = attributes.get('startDate', '')
            end_date_str = attributes.get('finishDate', '')
            
            if start_date_str and end_date_str:
                # Parse dates
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                
                iterations.append({
                    'name': iteration.get('name', 'Unknown Sprint'),
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d'),
                    'start_dt': start_date,
                    'end_dt': end_date
                })
        
        # Sort by start date
        iterations.sort(key=lambda x: x['start_dt'])
        
        # Debug: print iterations
        print(f"\nFound {len(iterations)} iterations:")
        for i, it in enumerate(iterations):
            print(f"  {i+1}. {it['name']}: {it['start']} to {it['end']}")
        
        return iterations
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching iterations: {e}")
        return None


def get_current_sprint_dates(pat):
    """
    Get dates spanning all iterations for team Kvoteklubben
    
    Args:
        pat: Personal Access Token for Azure DevOps
        
    Returns:
        dict with keys: 'name', 'start', 'end' (dates in YYYY-MM-DD format), 'iterations' (list of all sprints)
        or None if no iterations found
    """
    # Get all iterations
    iterations = get_all_iterations(pat)
    
    if not iterations:
        return None
    
    # Get earliest and latest dates
    earliest_start = iterations[0]['start']
    latest_end = iterations[-1]['end']
    
    print(f"\nDate range: {earliest_start} to {latest_end}")
    print(f"Today: {datetime.now().strftime('%Y-%m-%d')}\n")
    
    return {
        'name': f'All Iterations ({len(iterations)} sprints)',
        'start': earliest_start,
        'end': latest_end,
        'iterations': iterations
    }


if __name__ == "__main__":
    # Simple test - actual usage is in weekly_state_chart.py
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    pat = os.getenv('AZURE_DEVOPS_PAT')
    
    if not pat:
        print("Error: AZURE_DEVOPS_PAT environment variable not set")
        exit(1)
    
    sprint_info = get_current_sprint_dates(pat)
    
    if sprint_info:
        print(f"\n{sprint_info['name']}")
        print(f"Range: {sprint_info['start']} to {sprint_info['end']}")
        print(f"\nSprints:")
        for iteration in sprint_info.get('iterations', []):
            print(f"  • {iteration['name']}: {iteration['start']} → {iteration['end']}")
    else:
        print("Failed to retrieve sprint dates")
