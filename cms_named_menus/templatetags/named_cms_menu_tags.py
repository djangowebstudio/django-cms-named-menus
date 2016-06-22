from cms_named_menus import cache
import logging

from classytags.arguments import IntegerArgument, Argument, StringArgument
from classytags.core import Options
from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import get_language
from menus.templatetags.menu_tags import ShowMenu

from cms_named_menus.nodes import get_nodes
from cms_named_menus.models import CMSNamedMenu


logger = logging.getLogger(__name__)

register = template.Library()


class ShowMultipleMenu(ShowMenu):
    
    name = 'show_named_menu'

    options = Options(
        StringArgument('menu_name', required=True),
        IntegerArgument('from_level', default=0, required=False),
        IntegerArgument('to_level', default=100, required=False),
        IntegerArgument('extra_inactive', default=0, required=False),
        IntegerArgument('extra_active', default=1000, required=False),
        StringArgument('template', default='menu/menu.html', required=False),
        StringArgument('namespace', default=None, required=False),
        StringArgument('root_id', default=None, required=False),
        Argument('next_page', default=None, required=False),
    )

    def get_context(self, context, **kwargs):

        menu_name = kwargs.pop('menu_name')

        context.update({
            'children': [],
            'template': kwargs.get('template'),
            'from_level': kwargs.get('from_level'),
            'to_level': kwargs.get('to_level'),
            'extra_inactive': kwargs.get('extra_inactive'),
            'extra_active': kwargs.get('extra_active'),
            'namespace': kwargs.get('namespace')
        })

        lang = get_language()
        arranged_nodes = cache.get(menu_name, lang)
        if arranged_nodes is None:
            try:
                named_menu = CMSNamedMenu.objects.get(name__iexact=menu_name).pages
            except ObjectDoesNotExist:
                logging.warn("Named CMS Menu %s not found" % menu_name)
                arranged_nodes = []
            else:
                nodes = get_nodes(context['request'], kwargs['namespace'], kwargs['root_id'])
                arranged_nodes = self.arrange_nodes(nodes, named_menu, namespace=kwargs['namespace'])
            cache.set(menu_name, lang, arranged_nodes)
        context.update({
            'children': arranged_nodes
        })
        return context

    def arrange_nodes(self, node_list, node_config, namespace=None):
        arranged_nodes = []
        for item in node_config:
            item.update({'namespace': namespace})
            node = self.create_node(item, node_list)
            if node is not None:
                arranged_nodes.append(node)
        return arranged_nodes

    def create_node(self, item, node_list):
        item_node = self.get_node_by_id(item['id'], node_list, namespace=item['namespace'])
        if item_node is None:
            return None
        for child_item in item.get('children', []):
            child_node = self.get_node_by_id(child_item['id'], node_list, namespace=item['namespace'])
            if child_node is not None:
                item_node.children.append(child_node)
        return item_node

    def get_node_by_id(self, id, nodes, namespace=None):  # @ReservedAssignment
        final_node = None
        try:
            for node in nodes:
                if node.id == id:
                    if namespace:
                        if node.namespace == namespace:
                            final_node = node
                            break
                    else:
                        final_node = node
                        break
        except:
            logger.exception('Failed to find node')
        if final_node is not None:
            final_node.children = []
            final_node.parent = []
        return final_node


register.tag(ShowMultipleMenu)
