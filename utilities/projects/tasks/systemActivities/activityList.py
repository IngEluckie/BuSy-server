# activityList.py

# Import libraries
from typing import Dict

# Import modules
#from node_synching.node_sync import NSync
from utilities.projects.tasks.systemActivities.node_synching.node_sync import init_NSync

ActivityList: Dict = {
    "systemActivities": [init_NSync,]

}