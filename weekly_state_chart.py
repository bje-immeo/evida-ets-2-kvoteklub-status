import plotly.graph_objects as go
from weekly_task_state_tracker import WeeklyTaskStateTracker
from sprint_dates import get_all_iterations
from collections import defaultdict
from datetime import datetime
import os


def calculate_sprint_marker_position(sprint_date, weekly_data):
    """
    Calculate where to draw sprint marker on the categorical x-axis
    
    Args:
        sprint_date: datetime object of sprint start/end
        weekly_data: list of week buckets with start_dt and end_dt
    
    Returns:
        float: Position on x-axis (0.0 = first bar center, 1.0 = second bar center, etc.)
    """
    for i, week in enumerate(weekly_data):
        if week['start_dt'] <= sprint_date <= week['end_dt']:
            # Calculate fractional position within the week
            week_duration = (week['end_dt'] - week['start_dt']).days + 1
            days_into_week = (sprint_date - week['start_dt']).days
            fraction = days_into_week / week_duration if week_duration > 0 else 0
            
            # Return position: week index + fraction - 0.5 (bars are centered at integers)
            return i + fraction - 0.5
    
    # If not in range, return position relative to first/last week
    if sprint_date < weekly_data[0]['start_dt']:
        days_before = (weekly_data[0]['start_dt'] - sprint_date).days
        return -0.5 - (days_before / 7)
    else:
        days_after = (sprint_date - weekly_data[-1]['end_dt']).days
        return len(weekly_data) - 0.5 + (days_after / 7)


def create_weekly_state_chart():
    """Create a stacked bar chart showing task states over time"""
    # Get the data
    tracker = WeeklyTaskStateTracker()
    weekly_data = tracker.get_weekly_task_states()
    
    if not weekly_data:
        print("No data available")
        return
    
    # Convert date strings to datetime objects for marker positioning
    for week in weekly_data:
        week['start_dt'] = datetime.strptime(week['start_date'], '%Y-%m-%d')
        week['end_dt'] = datetime.strptime(week['end_date'], '%Y-%m-%d')
    
    # Get sprint iterations for markers
    iterations = get_all_iterations(tracker.pat)
    
    # Convert sprint dates to naive datetime for comparison with weekly data
    if iterations:
        for iteration in iterations:
            iteration['start_dt'] = iteration['start_dt'].replace(tzinfo=None)
            iteration['end_dt'] = iteration['end_dt'].replace(tzinfo=None)
    
    # Prepare data for plotting
    weeks = []
    week_start_dates = []  # Store week start dates for dual labels
    state_counts = defaultdict(list)
    
    # Get all unique states across all weeks
    all_states = set()
    for week in weekly_data:
        for task in week['tasks']:
            all_states.add(task['state'])
    
    # Process each week
    for week in weekly_data:
        # Create week label
        week_label = f"Week {week['week']} ({week['year']})"
        weeks.append(week_label)
        week_start_dates.append(week['start_dt'])
        
        # Count tasks by state for this week
        state_count = {}
        for task in week['tasks']:
            state = task['state']
            state_count[state] = state_count.get(state, 0) + 1
        
        # Add counts for all states (0 if state not present)
        for state in all_states:
            state_counts[state].append(state_count.get(state, 0))
    
    # Create the bar chart with "New" separate and others stacked
    fig = go.Figure()
    
    # Separate "New" from other states
    new_state = 'New'
    other_states = sorted([s for s in all_states if s != new_state])
    
    # Add "New" as a separate bar (not stacked)
    if new_state in state_counts:
        fig.add_trace(go.Bar(
            name=new_state,
            x=weeks,
            y=state_counts[new_state],
            text=state_counts[new_state],
            textposition='inside',
            legendgroup='new',
            offsetgroup='new'
        ))
    
    # Add stacked bars for all other states
    for state in other_states:
        fig.add_trace(go.Bar(
            name=state,
            x=weeks,
            y=state_counts[state],
            text=state_counts[state],
            textposition='inside',
            legendgroup='other',
            offsetgroup='other'
        ))
    
    # Add sprint markers as shaded regions with dashed lines
    if iterations:
        
        for idx, iteration in enumerate(iterations):
            start_pos = calculate_sprint_marker_position(iteration['start_dt'], weekly_data)
            end_pos = calculate_sprint_marker_position(iteration['end_dt'], weekly_data)
            
            # Add shaded region for sprint duration
            fig.add_vrect(
                x0=start_pos,
                x1=end_pos,
                opacity=0.3,
                layer="below",
                line_width=0,
                annotation_text=iteration['name'],
                annotation_position="top outside",
                annotation_font_size=10
            )
            
            # Add dashed line at sprint start
            fig.add_vline(
                x=start_pos,
                line_dash="dash",
                line_color="red",
                line_width=2,
                opacity=0.7
            )
    
    # Create custom tick labels with dates
    tick_text = []
    for week_label, start_date in zip(weeks, week_start_dates):
        date_str = start_date.strftime('%b %d')
        tick_text.append(f"{week_label}<br>{date_str}")
    
    # Update x-axis with dual labels
    fig.update_xaxes(
        ticktext=tick_text,
        tickvals=list(range(len(weeks)))
    )
    
    # Update layout
    fig.update_layout(
        title='Weekly Task States with Sprint Boundaries',
        xaxis_title='ISO Week (Start Date)',
        yaxis_title='Number of Tasks',
        barmode='stack',
        hovermode='x unified',
        height=650,
        showlegend=True,
        legend=dict(
            title='State',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.01
        ),
        margin=dict(b=100)  # Extra bottom margin for dual labels
    )
    
    # Save to dist/index.html
    os.makedirs('dist', exist_ok=True)
    output_path = os.path.join('dist', 'index.html')
    fig.write_html(output_path)
    print(f"Chart saved to {output_path}")


if __name__ == '__main__':
    create_weekly_state_chart()
