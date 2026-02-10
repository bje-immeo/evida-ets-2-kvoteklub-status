"""
Stacked Bar Chart Generator for Azure DevOps Features by Task Status
Creates horizontal bars for each feature with stacks showing task status distribution
"""

import plotly.graph_objects as go
from collections import defaultdict, Counter
from azure_devops_query import AzureDevOpsClient
import os

class FeatureTaskStatusChart:
    def __init__(self):
        self.feature_task_status = defaultdict(Counter)
        
    def prepare_data(self, task_data):
        """
        Process task hierarchy data to group task statuses by feature
        Hierarchy: Feature -> User Story -> Task (US is just for linking)
        """
        # Group tasks by feature and count statuses
        for task in task_data:
            feature = task['feature_title']
            task_status = task['task_state']
            
            # Count task statuses per feature
            self.feature_task_status[feature][task_status] += 1
            
        return len(self.feature_task_status)
    
    def create_stacked_bar_chart(self, title="Azure DevOps Features - Task Status Distribution"):
        """Create horizontal stacked bar chart"""
        
        # Get all unique task statuses across all features
        all_statuses = set()
        for feature_statuses in self.feature_task_status.values():
            all_statuses.update(feature_statuses.keys())
        all_statuses = sorted(list(all_statuses))
        
        # Prepare data for plotting
        features = sorted(list(self.feature_task_status.keys()))
        
        # Define colors for different statuses
        status_colors = {
            'New': '#1f77b4',           # Blue
            'Active': "#0eff8f",        # Orange  
            'Resolved': '#2ca02c',      # Green
            'Closed': "#4ad627",        # Red
            'Removed': '#9467bd',       # Purple
            'To Do': '#8c564b',         # Brown
            'In Progress': '#e377c2',   # Pink
            'Done': '#7f7f7f',          # Gray
            'Committed': '#bcbd22',     # Olive
            'Approved': '#17becf'       # Cyan
        }
        
        # Create horizontal stacked bar chart
        fig = go.Figure()
        
        for status in all_statuses:
            # Get count for each feature for this status
            counts = []
            for feature in features:
                count = self.feature_task_status[feature].get(status, 0)
                counts.append(count)
            
            fig.add_trace(go.Bar(
                name=status,
                y=features,
                x=counts,
                orientation='h',
                marker_color=status_colors.get(status, '#000000'),
                hovertemplate='<b>%{y}</b><br>' +
                             f'{status}: %{{x}}<br>' +
                             '<extra></extra>'
            ))
        
        # Update layout for horizontal bars
        fig.update_layout(
            title=title,
            xaxis_title="Number of Tasks",
            yaxis_title="Features",
            barmode='stack',
            height=max(400, len(features) * 40),  # Dynamic height based on number of features
            width=1200,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            margin=dict(l=300, r=150, t=50, b=50)  # Extra left margin for feature names
        )
        
        # Sort features alphabetically
        fig.update_yaxes(categoryorder='category descending')
        
        return fig
        
    def generate_from_azure_devops(self):
        """Generate stacked bar chart from live Azure DevOps data"""
        try:
            client = AzureDevOpsClient()
            task_data = client.get_task_hierarchy_data()
            
            if not task_data:
                print("No task data retrieved from Azure DevOps")
                return None
                
            print(f"Retrieved {len(task_data)} tasks from Azure DevOps")
            
            # Prepare data 
            features_count = self.prepare_data(task_data)
            print(f"Found {features_count} features")
            
            # Create chart
            fig = self.create_stacked_bar_chart()
            
            return fig, task_data
            
        except Exception as e:
            print(f"Error generating chart: {e}")
            return None, None

def main():
    """Main function to generate and display/save stacked bar chart"""
    chart_generator = FeatureTaskStatusChart()
    figure, data = chart_generator.generate_from_azure_devops()
    
    if figure:
        # Show the chart in browser
        figure.show()
        
        # Create dist folder if it doesn't exist
        os.makedirs('dist', exist_ok=True)
        
        # Save as HTML in dist folder
        output_path = os.path.join('dist', 'index.html')
        figure.write_html(output_path)
        print(f"Stacked bar chart saved as '{output_path}'")
        
        # Print summary statistics
        print(f"\nChart Summary:")
        print(f"- Total tasks: {len(data)}")
        print(f"- Features: {len(set(task['feature_title'] for task in data))}")
        
        # Show task status distribution
        all_statuses = Counter()
        for task in data:
            all_statuses[task['task_state']] += 1
            
        print(f"- Task Status Distribution:")
        for status, count in all_statuses.most_common():
            print(f"  {status}: {count}")
            
        # Show features and their task counts
        feature_task_counts = Counter()
        for task in data:
            feature_task_counts[task['feature_title']] += 1
            
        print(f"\n- Features by Task Count:")
        for feature, count in feature_task_counts.most_common():
            print(f"  {feature}: {count} tasks")
        
    else:
        print("Failed to generate stacked bar chart")

if __name__ == "__main__":
    main()