import importlib
import inspect
import pkgutil
from typing import Dict


class ProviderResources():
    def __init__(self) -> None:
        self._provider_resources_dict = self.__init_provider_resources()
        pass

    @property
    def provider_resources(self):
        return self._provider_resources_dict

    def __init_provider_resources(self) -> Dict:
        """
        Inspects nested class from 'diagrams' package to produce available 'Nodes'
        (providers services). See: https://diagrams.mingrammer.com/docs/nodes/aws.
        Every provider has a dictionary of category and every category has a list of available services
        
        Return: Dict
        """
        def add_provider(provider_name: str) -> None:
            if provider_name not in providers_dict:
                providers_dict.update({provider_name: {}})

        def add_category(provider_name:str, category_name: str) -> None:
            if category_name not in providers_dict[provider_name]:
                providers_dict[provider_name].update({category_name: []})

        def add_service(provider_name:str, category_name:str, service_name:str) -> None:
            add_provider(provider_name=provider_name)
            add_category(provider_name=provider_name, category_name=category_name)
            if service_name not in providers_dict[provider_name][category_name]:
                providers_dict[provider_name][category_name].append(service_name)

        package_name='diagrams'
        providers_dict = {}
        # Import the top-level package
        package = importlib.import_module(package_name)
        
        # Walk through all submodules and subpackages
        for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
            if not is_pkg:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Inspect all members of the module
                for name, obj in inspect.getmembers(module):
                    # Check if the member is a class and belongs to the module (excluding imported classes)
                    if inspect.isclass(obj) and obj.__module__ == module.__name__:

                        if not name.startswith('_'):
                            _, provider_name, category_name = module_name.split('.')
                            add_service(provider_name=provider_name,
                                        category_name=category_name,
                                        service_name=name)
            else:
                _, provider_name = module_name.split('.')
                add_provider(provider_name=provider_name)    
        return providers_dict