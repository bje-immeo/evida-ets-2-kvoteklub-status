import os
import requests
import base64
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AzureDevOpsClient:
    def __init__(self):
        self.pat = os.getenv('AZURE_DEVOPS_PAT')
        if not self.pat:
            raise ValueError("AZURE_DEVOPS_PAT not found in .env file")
        
        # Create authorization header
        encoded_pat = base64.b64encode(f':{self.pat}'.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_pat}',
            'Content-Type': 'application/json'
        }
        
        # Parse the query URL components
        self.organization = 'EvidaDevops'
        self.project = 'ETS2'
        self.tasks_query_id = '197b9a9b-22fa-4cfe-a7d9-10f4c5d17612'  # Original tasks query
        self.userstories_query_id = '39578a2d-6412-49c8-b720-aff6c100a2b5'  # User stories query
        
    def execute_query(self, query_id, query_name):
        """Execute a single query and return work item IDs"""
        wiql_url = f'https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/wiql/{query_id}'
        
        response = requests.get(wiql_url, headers=self.headers, params={'api-version': '6.0'})
        response.raise_for_status()
        results = response.json()
        
        work_items = results.get('workItems', [])
        
        return [item['id'] for item in work_items]
    
    def get_work_item_details(self, work_item_ids):
        """Get detailed work item information"""
        if not work_item_ids:
            return []
            
        details_url = f'https://dev.azure.com/{self.organization}/{self.project}/_apis/wit/workitems'
        details_params = {
            'ids': ','.join([str(id) for id in work_item_ids]),
            'api-version': '7.0',
            '$expand': 'all'
        }
        
        response = requests.get(details_url, headers=self.headers, params=details_params)
        response.raise_for_status()
        
        result = response.json()
        

        
        return result.get('value', [])
    
    def get_task_hierarchy_data(self):
        """Get task hierarchy data with user stories and features - returns structured data"""
        # Get work items from both queries
        task_ids = self.execute_query(self.tasks_query_id, "tasks")
        userstory_ids = self.execute_query(self.userstories_query_id, "user stories")
        
        # Get all work item IDs we need
        all_work_item_ids = list(set(task_ids + userstory_ids))
        
        all_work_items = self.get_work_item_details(all_work_item_ids)
        
        # Create lookup dictionaries
        work_items_by_id = {item['id']: item for item in all_work_items}
        
        # Find parent relationships and get feature IDs
        feature_ids = set()
        for item in all_work_items:
            relations = item.get('relations', [])
            for relation in relations:
                if relation.get('rel') == 'System.LinkTypes.Hierarchy-Reverse':
                    # This work item has a parent
                    parent_url = relation.get('url', '')
                    if 'workItems/' in parent_url:
                        parent_id = int(parent_url.split('workItems/')[-1])
                        if parent_id not in work_items_by_id:
                            feature_ids.add(parent_id)
        
        # Get feature details if any
        if feature_ids:
            feature_details = self.get_work_item_details(list(feature_ids))
            for feature in feature_details:
                work_items_by_id[feature['id']] = feature
        
        # Process results and return structured data
        results = []
        
        for task_id in task_ids:
            task = work_items_by_id.get(task_id)
            if not task:
                continue
            
            task_fields = task.get('fields', {})
            task_title = task_fields.get('System.Title', 'No title')
            task_state = task_fields.get('System.State', 'Unknown')
            task_tags = task_fields.get('System.Tags', '')
            
            # Find parent user story
            parent_us_id = None
            relations = task.get('relations', [])
            
            for relation in relations:
                rel_type = relation.get('rel', '')
                if rel_type == 'System.LinkTypes.Hierarchy-Reverse':
                    parent_url = relation.get('url', '')
                    if 'workItems/' in parent_url:
                        parent_us_id = int(parent_url.split('workItems/')[-1])
                        break
            
            us_title = "No parent US"
            us_state = "N/A"
            feature_title = "No parent Feature"

            if parent_us_id and parent_us_id in work_items_by_id:
                parent_us = work_items_by_id[parent_us_id]
                us_fields = parent_us.get('fields', {})
                us_title = us_fields.get('System.Title', 'No title')
                us_state = us_fields.get('System.State', 'Unknown')
                
                # Find parent feature of the user story
                us_relations = parent_us.get('relations', [])
                for relation in us_relations:
                    if relation.get('rel') == 'System.LinkTypes.Hierarchy-Reverse':
                        feature_url = relation.get('url', '')
                        if 'workItems/' in feature_url:
                            feature_id = int(feature_url.split('workItems/')[-1])
                            if feature_id in work_items_by_id:
                                feature = work_items_by_id[feature_id]
                                feature_fields = feature.get('fields', {})
                                feature_title = feature_fields.get('System.Title', 'No title')
                            break
            
            # Create structured result
            task_data = {
                'task_id': task_id,
                'task_title': task_title,
                'task_state': task_state,
                'task_tags': task_tags if task_tags else 'None',
                'us_title': us_title,
                'us_state': us_state,
                'feature_title': feature_title,
                'parent_us_id': parent_us_id
            }
            
            results.append(task_data)
        
        return results