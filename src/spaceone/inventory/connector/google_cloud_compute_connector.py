__all__ = ["GoogleCloudComputeConnector"]

import logging
import os
import itertools
import re
import google.oauth2.service_account
import googleapiclient
import googleapiclient.discovery
from pprint import pprint
from spaceone.core.connector import BaseConnector
from spaceone.core.utils import deep_merge
from collections import defaultdict

_LOGGER = logging.getLogger(__name__)
INSTANCE_TYPE_FILE = '%s/conf/%s' % (os.path.dirname(os.path.abspath(__file__)), 'instances.json')


class GoogleCloudComputeConnector(BaseConnector):

    def __init__(self, transaction=None, config=None):
        self.client = None
        self.project_id = None
        self.region = None
        self.zone = None

    def verify(self, options, secret_data):
        self.get_connect(secret_data)
        return "ACTIVE"

    def get_connect(self, secret_data):
        """
        cred(dict)
            - type: ..
            - project_id: ...
            - token_uri: ...
            - ...
        """
        try:
            self.project_id = secret_data.get('project_id')
            credentials = google.oauth2.service_account.Credentials.from_service_account_info(secret_data)
            return googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
        except Exception as e:
            print(e)
            raise self.client(message='connection failed. Please check your authentication information.')

    def list_regions(self):
        result = self.client.regions().list(project=self.project_id).execute()
        return result.get('items', [])

    def list_zones(self):
        result = self.client.zones().list(project=self.project_id).execute()
        return result.get('items', [])

    def list_instances(self, **query):
        status_filter = {'key': 'status', 'values': ['STAGING', 'RUNNING', 'STOPPING', 'REPAIRING']}

        if 'filter' in query:
            query.get('filter').append(status_filter)
        else:
            query.update({'filter': [status_filter]})

        query = self.generate_key_query('filter', self._get_filter_to_params(**query), '', is_default=True, **query)
        result = self.client.instances().list(**query).execute()
        compute_instances = result.get('items', [])
        return compute_instances

    def list_machine_types(self, **query):
        query = self.generate_query(**query)
        result = self.client.machineTypes().list(**query).execute()
        instance_types = result.get('items', [])
        return instance_types

    def list_url_maps(self, **query):
        query = self.generate_query(**query)
        response = self.client.urlMaps().list(project=self.project_id).execute()
        url_map = response.get('items', [])
        return url_map

    def list_disk(self, **query):
        response = self.client.disks().list(project=self.project_id, zone=self.zone).execute()
        disks = response.get('items', [])
        return disks

    def list_disk_types(self, **query):
        response = self.client.diskTypes().list(project=self.project_id, zone=self.zone).execute()
        disks_types = response.get('items', [])
        return disks_types

    def list_auto_scalers(self, **query):
        response = self.client.autoscalers().list(project=self.project_id, zone=self.zone).execute()
        auto_scaler = response.get('items', [])
        return auto_scaler

    def list_firewalls(self, **query):
        response = self.client.firewalls().list(project=self.project_id).execute()
        firewall = response.get('items', [])
        return firewall

    def list_images(self, **query):
        response = self.client.images().list(project=self.project_id).execute()
        firewall = response.get('items', [])
        return firewall

    def list_instance_groups(self, **query):
        response = self.client.instanceGroups().list(project=self.project_id).execute()
        firewall = response.get('items', [])
        return firewall

    def list_instance_from_instance_groups(self, **query):
        query = self.generate_query(**query)
        response = self.client.instanceGroups().listInstances(**query).execute()
        firewall = response.get('items', [])
        return firewall

    def list_instance_group_managers(self, **query):
        response = self.client.instanceGroupManagers().list(project=self.project_id, zone=self.zone).execute()
        firewall = response.get('items', [])
        return firewall

    def list_vpcs(self, **query):
        query = self.generate_query(**query)
        response = self.client.networks().list(**query).execute()
        return response.get('items', [])

    def list_subnets(self, **query):
        query = self.generate_query(**query)
        response = self.client.subnetworks().list(**query).execute()
        return response.get('items', [])

    def list_forwarding_rules(self, **query):
        query = self.generate_query(**query)
        response = self.client.forwardingRules().list(**query).execute()
        return response.get('items', [])

    # bluese-cloudone-20200113
    #===== [asia-northeast3-a]

    def _get_filter_to_params(self, **query):
        filtering_list = []
        filters = query.get('filter', None)
        if filters and isinstance(filters, list):
            for single_filter in filters:
                filter_key = single_filter.get('key', '')
                filter_values = single_filter.get('values', [])
                filter_str = self._get_full_filter_string(filter_key, filter_values)
                if filter_str != '':
                    filtering_list.append(filter_str)

            return ' AND '.join(filtering_list)

    def generate_query(self, **query):
        query.update({
            'project': self.project_id,
        })
        return query

    def generate_key_query(self, key, value, delete, is_default=False, **query):
        if is_default:
            if delete != '':
                query.pop(delete, None)

            query.update({
                key: value,
                'project': self.project_id,
                'zone': self.zone
            })

        return query

    @staticmethod
    def get_region(zone):
        index = zone.find('-')
        region = zone[0:index] if index > -1 else ''
        return region

    @staticmethod
    def _get_full_filter_string(filter_key, filter_values):
        filter_string = ''
        if filter_key != '' and filter_values != [] and isinstance(filter_values, list):
            single_filter_list = [f'{filter_key}={x}' for x in filter_values]
            join_string = ' OR '.join(single_filter_list)
            filter_string = f'({join_string})'
        elif filter_key != '' and filter_values != [] and not isinstance(filter_values, dict):
            filter_string = f'({filter_key}={filter_values})'
        return filter_string