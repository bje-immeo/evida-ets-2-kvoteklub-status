# Evida ETS-2 Kvoteklubben Status Tracker

A Python tool for tracking and visualizing sprint progress for the **Kvoteklubben** team in Azure DevOps. This tool automatically finds all sprints for the team and generates status charts showing task progress over time.

## Features

- **Weekly Task State Charts**: Visualize task states (New, Active, Resolved, Closed, etc.) across sprint weeks
- **Feature Status Charts**: View task distribution by feature with horizontal stacked bar charts
- **Sprint Milestone Markers**: Automatic sprint start/end markers on charts
- **Automatic Sprint Detection**: Finds all configured iterations for the Kvoteklubben team

## Prerequisites

- Python 3.7+
- Azure DevOps Personal Access Token (PAT) with work item read permissions
- Access to the Evida ETS2 Azure DevOps project

## Installation

1. Clone this repository
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your Azure DevOps PAT:
   ```
   AZURE_DEVOPS_PAT=your_personal_access_token_here
   ```

## Configuration

### Modifying Sprint Milestones

The tool automatically finds all sprints (iterations) configured for the **Kvoteklubben** team.

To modify what milestones/sprints are displayed:

1. Navigate to the team settings page:
   [https://dev.azure.com/EvidaDevops/ETS2/_settings/work-team?teamId=b0f8c5d3-a435-4dee-a097-848c223eec90](https://dev.azure.com/EvidaDevops/ETS2/_settings/work-team?teamId=b0f8c5d3-a435-4dee-a097-848c223eec90)

2. Click **Iterations**

3. Add the sprint iterations you need

4. **Important**: Ensure to add dates for each iteration

The tool will automatically pick up these configured iterations when generating charts.

## Usage

### Generate Weekly State Chart

```bash
python weekly_state_chart.py
```

This will:
- Query all tasks from the team's backlog
- Group tasks by week
- Create a stacked bar chart showing task states over time
- Display sprint start/end markers
- Open the chart in your default browser

## Known Behavior / Important Notes

### Baseline Calculation Behavior

⚠️ **Important**: The tool sums **all tasks currently in the backlog** when calculating historical data. 

**What this means**:
- If you suddenly add 50 new tasks to the backlog today, the charts will retroactively show those tasks in all previous weeks
- This makes it appear as if the tasks were there from the start
- The baseline value is calculated through all weeks based on the current backlog state

## Project Structure

- `weekly_state_chart.py` - Generates weekly task state visualization
- `weekly_task_state_tracker.py` - Core logic for tracking task states over time
- `azure_devops_query.py` - Azure DevOps API client for querying work items
- `sprint_dates.py` - Retrieves sprint/iteration dates from Azure DevOps
- `requirements.txt` - Python dependencies
- `.env` - Configuration file (not in repo - you must create this)

## Dependencies

- `requests` - HTTP library for Azure DevOps API calls
- `python-dotenv` - Environment variable management
- `plotly` - Interactive chart generation

## Team Information

- **Organization**: EvidaDevops
- **Project**: ETS2
- **Team**: Kvoteklubben
- **Team ID**: b0f8c5d3-a435-4dee-a097-848c223eec90

## Troubleshooting

### No data available
- Ensure your PAT token has the correct permissions
- Verify you have access to the ETS2 project
- Check that iterations are configured with dates

### Charts not displaying sprint markers
- Verify iterations have start and end dates in Azure DevOps
- Ensure the iteration paths are correctly assigned to the team

### Authentication errors
- Check that your `AZURE_DEVOPS_PAT` is set correctly in the `.env` file
- Verify your PAT hasn't expired
- Ensure the PAT has "Work Items (Read)" permissions

## License

Internal Evida tool - for team use only.
