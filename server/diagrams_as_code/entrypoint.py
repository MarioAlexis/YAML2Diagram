"""
Provide implementation of `diagrams` as a code using YAML.
"""
import importlib
import os
import sys
import yaml
import base64
from diagrams import (
    Cluster,
    Diagram,
    Edge,
    Node,
)
from diagrams_as_code.enums import (
    ServiceResourceType,
    RelationDirection,
)
from diagrams_as_code.resources import DiagramGroup
from diagrams_as_code.schema import (
    Relationship,
    YamlDiagram,
    YamlDiagramResource,
)

resources = {}
relationships = []


def get_diagram_node_class(path: str) -> Node:
    """
    Get a `diagrams` node class.

    The common example of a path is `aws.analytics.Analytics` which strongly correlates to `diagrams` real defined
    classes. In the example, `Analytics` is a class, the rest `aws.analytics` is a few modules. Basically, there
    are the modules are loaded and then the class is got on fly.

    It helps to reuse the same «path» in both YAML files and execution of classes without a need of redeclaration.

    Arguments:
        path (str): a path to class.

    References:
        - https://diagrams.mingrammer.com/docs/nodes/aws

    Returns:
        The node's class as a `Node`.
    """
    provider, resource, service = path.split('.')

    module = importlib.import_module(f'diagrams.{provider}.{resource}')
    class_ = getattr(module, service)

    return class_


def process_resource(resource: YamlDiagramResource, parent_id: str, group: DiagramGroup = None) -> None:
    """
    Process a resource.

    Basically, this function is recursive because `YAML` file can contain infinite number of configurations. There might
    be a single node (such as EC2 or RDS), a group of nodes and a cluster of nodes and groups further.

    All nodes are stored by unique identifiers in a global storage (`resources`) and then easily fetched from there
    to build relationships. For this, there is a need to always pass parent's resource identifier to have unique
    identifier for each node.

    There is also the resource called `group` which is literary a list of nodes to which other things relate to.

    Arguments:
        resource (YamlDiagramResource): a resource.
        parent_id (str): a parent's identifier.
        group (DiagramGroup): a group.
    """
    if resource.type == ServiceResourceType.CLUSTER.value:
        cluster = Cluster(label=resource.name)
        cluster.__enter__()

        if resource.of is not None:
            for resource_of in resource.of:
                process_resource(resource=resource_of, parent_id=f'{parent_id}.{resource.id}')

        cluster.__exit__(None, None, None)

    if resource.type == ServiceResourceType.GROUP.value:
        diagram_group = DiagramGroup()

        resources.update({
            f'{parent_id}.{resource.id}': diagram_group,
        })

        if resource.relates is not None:
            for relation in resource.relates:
                relationship = Relationship(
                    from_=f'{parent_id}.{resource.id}',
                    to=f'diagram.{relation.to}',
                    direction=relation.direction,
                    label=relation.label,
                    color=relation.color,
                    style=relation.style,
                )

                relationships.append(relationship)

        if resource.of is not None:
            for resource_of in resource.of:
                process_resource(resource=resource_of, parent_id=f'{parent_id}.{resource.id}', group=diagram_group)

    if (
        resource.type != ServiceResourceType.CLUSTER.value and
        resource.type != ServiceResourceType.GROUP.value
    ):
        resource_instance = get_diagram_node_class(path=resource.type)(label=resource.name)

        resources.update({
            f'{parent_id}.{resource.id}': resource_instance,
        })

        # Check if relates is defined
        if resource.relates is not None:
            for relation in resource.relates:
                relationship = Relationship(
                    from_=f'{parent_id}.{resource.id}',
                    to=f'diagram.{relation.to}',
                    direction=relation.direction,
                    label=relation.label,
                    color=relation.color,
                    style=relation.style,
                )

                relationships.append(relationship)

        if group is not None:
            group.add_node(node=resource_instance)


def entrypoint(yaml_file_path: str) -> str:
    """
    yaml2diagram

    Arguments:
    yaml: dict representing YAML data structure

    Return:
    str: image base64 encoded string
    """
    global resources
    global relationships

    with open(yaml_file_path) as yaml_file:
        yaml_as_dict = yaml.safe_load(yaml_file)

    diagram_as_dict = yaml_as_dict.get('diagram')
    diagram = YamlDiagram(**diagram_as_dict)

    # TODO: figure out how to pass empty `YamlDiagramStyle` to `diagram.style` in Pydantic to remove the if condition.
    graph_style = Diagram._default_graph_attrs | diagram.style.graph if diagram.style else {}
    node_style = Diagram._default_node_attrs | diagram.style.node if diagram.style else {}
    edge_style = Diagram._default_edge_attrs | diagram.style.edge if diagram.style else {}

    with Diagram(
        name='',
        filename=diagram.file_name,
        direction=diagram.direction.mapped,
        outformat=diagram.format,
        autolabel=diagram.label_resources,
        show=False,
        graph_attr=graph_style,
        node_attr=node_style,
        edge_attr=edge_style,
    ) as diag:
        for resource in diagram.resources:
            process_resource(resource, 'diagram')

        for relationship in relationships:
            edge = Edge(label=relationship.label, color=relationship.color, style=relationship.style)

            resource_from_instance = resources.get(relationship.from_)
            resource_to_instance = resources.get(relationship.to)

            if resource_to_instance is None:
                resource_to_identifier_from_configs = relationship.to.replace('diagram.', '')

                raise ValueError(
                    f"There is no such a resource's identifier to relate to: {resource_to_identifier_from_configs}",
                )

            is_resource_from_node = not isinstance(resource_from_instance, DiagramGroup)
            is_resource_from_group = isinstance(resource_from_instance, DiagramGroup)

            is_resource_to_node = not isinstance(resource_to_instance, DiagramGroup)
            is_resource_to_group = isinstance(resource_to_instance, DiagramGroup)

            if is_resource_from_node and is_resource_to_node:
                if relationship.direction == RelationDirection.INCOMING:
                    resource_from_instance.__lshift__(other=edge)
                    edge.__lshift__(other=resource_to_instance)

                if relationship.direction == RelationDirection.OUTGOING:
                    resource_from_instance.__rshift__(other=edge)
                    edge.__rshift__(other=resource_to_instance)

                if relationship.direction == RelationDirection.BIDIRECTIONAL:
                    resource_from_instance.__rshift__(other=edge)
                    edge.__lshift__(other=resource_to_instance)

                if relationship.direction == RelationDirection.UNDIRECTED:
                    resource_from_instance.__sub__(other=edge)
                    edge.__sub__(other=resource_to_instance)

            if is_resource_from_group and is_resource_to_node:
                group_nodes = resource_from_instance.get_nodes()

                if relationship.direction == RelationDirection.INCOMING:
                    group_nodes_edges = edge.__rlshift__(other=group_nodes)
                    resource_to_instance.__rlshift__(other=group_nodes_edges)

                if relationship.direction == RelationDirection.OUTGOING:
                    group_nodes_edges = edge.__rrshift__(other=group_nodes)
                    resource_to_instance.__rrshift__(other=group_nodes_edges)

                if relationship.direction == RelationDirection.BIDIRECTIONAL:
                    group_nodes_edges = edge.__rrshift__(other=group_nodes)
                    resource_to_instance.__rlshift__(other=group_nodes_edges)

                if relationship.direction == RelationDirection.UNDIRECTED:
                    group_nodes_edges = edge.__rsub__(other=group_nodes)
                    resource_to_instance.__rsub__(other=group_nodes_edges)

            if is_resource_from_node and is_resource_to_group:
                group_nodes = resource_to_instance.get_nodes()

                if relationship.direction == RelationDirection.INCOMING:
                    resource_from_instance.__lshift__(other=edge)
                    edge.__lshift__(other=group_nodes)

                if relationship.direction == RelationDirection.OUTGOING:
                    resource_from_instance.__rshift__(other=edge)
                    edge.__rshift__(other=group_nodes)

                if relationship.direction == RelationDirection.BIDIRECTIONAL:
                    resource_from_instance.__rshift__(other=edge)
                    edge.__lshift__(other=group_nodes)

                if relationship.direction == RelationDirection.UNDIRECTED:
                    resource_from_instance.__sub__(other=edge)
                    edge.__sub__(other=group_nodes)
    resources = {}
    relationships = []
    return base64.b64encode(diag._repr_png_()).decode('utf-8')

