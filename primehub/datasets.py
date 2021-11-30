import json
from typing import Iterator, Optional

from primehub import Helpful, cmd, Module, primehub_load_config
from primehub.utils import PrimeHubException
from primehub.utils.optionals import file_flag, toggle_flag
from primehub.utils.validator import ValidationSpec

DATASETS_ROOT = '/datasets/'


def invalid_config(message: str):
    example = """
    {"id":"my-dataset-name","tags":["my-tag-1", "my-tag-2"]}
    """.strip()
    raise PrimeHubException(message + "\n\nExample:\n" + json.dumps(json.loads(example), indent=2))


class Datasets(Helpful, Module):

    @cmd(name='create', description='Create a datasets', optionals=[('file', file_flag)])
    def _create(self, **kwargs) -> dict:
        """
        Create a datasets

        :type file: str
        :param file: The file path of a datasets configuration

        :rtype dict
        :return The information of the datasets
        """

        config = primehub_load_config(filename=kwargs.get('file', None))
        if not config:
            invalid_config('PrimeHub datasets configuration is required.')

        return self.create(config)

    def create(self, config: dict):
        """
        Create a datasets

        :type config: dict
        :param config: The configuration of the dataset

        :rtype dict
        :return The information of the datasets
        """
        query = """
        mutation CreateDatasetMutation($payload: DatasetV2CreateInput!) {
          createDatasetV2(data: $payload) {
            id
            name
            createdBy
            createdAt
            updatedAt
            tags
            size
          }
        }
        """
        config['groupName'] = self.group_name
        validate_creation(config)
        results = self.request({'payload': config}, query)
        if 'data' in results:
            return results['data']['createDatasetV2']
        return results

    @cmd(name='update', description='Update a dataset', optionals=[('file', file_flag)])
    def _update_cmd(self, dataset_id: str, **kwargs) -> dict:
        """
        Update the dataset

        :type dataset_id: str
        :param dataset_id: The id of a dataset

        :type file: str
        :param file: The file path of a dataset configuration

        :rtype dict
        :return The information of the dataset
        """

        config = primehub_load_config(filename=kwargs.get('file', None))
        if not config:
            invalid_config('PrimeHub dataset configuration is required.')
        return self.update(dataset_id, config)

    def update(self, dataset_id: str, config: dict):
        """
        Update the dataset

        :type dataset_id: str
        :param dataset_id: The id of a dataset

        :type config: dict
        :param config: The configuration of the dataset

        :rtype dict
        :return The information of the dataset
        """

        query = """
        mutation UpdateDatasetMutation(
          $payload: DatasetV2UpdateInput!
          $where: DatasetV2WhereUniqueInput!
        ) {
          updateDatasetV2(data: $payload, where: $where) {
            id
            name
            createdBy
            createdAt
            updatedAt
            tags
            size
          }
        }
        """
        validate_update(config)
        variables = {'payload': config, 'where': {'id': dataset_id, 'groupName': self.group_name}}
        results = self.request(variables, query)
        if 'data' in results:
            return results['data']['updateDatasetV2']
        return results

    @cmd(name='list', description='List datasets', return_required=True, optionals=[('page', int)])
    def list(self, **kwargs) -> Iterator:
        """
        List all datasets information in the current group

        :type page: int
        :param page: the page number as you can see in PrimeHub datasets UI

        :rtype: Iterator
        :return: datasets iterator
        """

        query = """
        query GetDatasets($where: DatasetV2WhereInput, $page: Int) {
          datasetV2Connection(where: $where, page: $page) {
            edges {
              cursor
              node {
                id
                name
                createdBy
                createdAt
                updatedAt
                tags
                size
              }
            }
            pageInfo {
              currentPage
              totalPage
            }
          }
        }
        """
        variables = {'page': 1, 'where': {'groupName': self.group_name}}
        page = kwargs.get('page', 0)
        if page:
            variables['page'] = page
            results = self.request(variables, query)
            for e in results['data']['datasetV2Connection']['edges']:
                yield e['node']
            return

        page = 1
        while True:
            variables['page'] = page
            results = self.request(variables, query)
            if results['data']['datasetV2Connection']['edges']:
                for e in results['data']['datasetV2Connection']['edges']:
                    yield e['node']
                page = page + 1
            else:
                break

    @cmd(name='get', description='Get the dataset', return_required=True)
    def get(self, dataset_id: str) -> Optional[dict]:
        """
        Get detail information of a datasets by id

        :type dataset_id: str
        :param dataset_id: the id of a dataset

        :rtype: Optional[dict]
        :returns: the detail information of a dataset
        """

        query = """
        query DatasetQuery($where: DatasetV2WhereUniqueInput!) {
          datasetV2(where: $where) {
            id
            name
            createdBy
            createdAt
            updatedAt
            tags
            size
          }
        }
        """
        variables = {'where': {'id': dataset_id, 'groupName': self.group_name}}
        result = self.request(variables, query)
        return result['data']['datasetV2']

    @cmd(name='delete', description='Delete the dataset', return_required=True)
    def delete(self, dataset_id) -> dict:
        """
        Delete a dataset by id

        :type dataset_id: str
        :param dataset_id: the id of the dataset

        :rtype dict
        :return the result of the deleted dataset
        """

        query = """
        mutation DeleteDatasetMutation($where: DatasetV2WhereUniqueInput!) {
          deleteDatasetV2(where: $where) {
            id
          }
        }
        """
        variables = {'where': {'id': dataset_id, 'groupName': self.group_name}}
        result = self.request(variables, query)
        if 'data' in result and 'deleteDatasetV2' in result['data']:
            return result['data']['deleteDatasetV2']
        return result

    @cmd(name='files-list', description='lists files of the dataset', return_required=True)
    def files_list(self, path) -> dict:
        """
        List files of the dataset by path

        :type path: str
        :param path: the path of the dataset

        :rtype dict
        :return the files information of the path in the dataset
        """

        full_path = DATASETS_ROOT + path
        result = self.primehub.files.list(full_path)
        return result

    @cmd(name='files-upload', description='upload files to the dataset', optionals=[('recursive', toggle_flag)])
    def files_upload(self, src, path, **kwargs):
        """
        Upload files to the dataset by path

        :type src: str
        :param src: the path of a local file or local directory

        :type path: str
        :param path: the path of the dataset

        :type recursive: bool
        :param recursive: copy recursively, set it when the source is a directory
        """

        full_path = DATASETS_ROOT + path
        result = self.primehub.files.upload(src, full_path, **kwargs)
        return result

    @cmd(name='files-download', description='download files from the dataset', optionals=[('recursive', toggle_flag)])
    def files_download(self, path, dest, **kwargs) -> dict:
        """
        Download files of the dataset by path

        :type path: str
        :param path: the path of a file or a directory

        :type dest: str
        :param dest: the local path to save files

        :type recursive: bool
        :param recursive: copy recursively, set it when the path is a directory
        """

        full_path = DATASETS_ROOT + path
        result = self.primehub.files.download(full_path, dest, **kwargs)
        return result

    def help_description(self):
        return "Manage datasets"


def validate_creation(config):
    spec = ValidationSpec("""
    input DatasetV2CreateInput {
      id: String!
      groupName: String!
      tags: StringList
    }
    """)
    spec.validate(config)


def validate_update(config):
    spec = ValidationSpec("""
    input DatasetV2UpdateInput {
      groupName: String
      tags: StringList
    }
    """)
    spec.validate(config)
