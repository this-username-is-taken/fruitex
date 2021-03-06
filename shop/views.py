from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist

import json

from shop.models import Store, Category, Item, ItemMeta, ItemMetaFilter

ITEM_PER_PAGE = 12
POPULAR_ITEM_PER_PAGE = 10
ON_SALE_ITEM_PER_PAGE = 5
FEATURED_ITEM_PER_PAGE = 5

# Common operations

def empty_response():
  return HttpResponse('[]', mimetype='application/json')

def items_response(items):
  encoded = serializers.serialize('json', items)
  decoded = json.loads(encoded)

  for i, item in enumerate(items.all()):
    item_metas = {}
    for meta in item.metas.all():
      item_metas[meta.key] = meta.value
    decoded[i]['fields']['metas'] = item_metas
  encoded = json.dumps(decoded)

  return HttpResponse(encoded, mimetype='application/json')

def common_context(request, store_slug):
  # Fetch all stores, current store and base categories of current store
  try:
    stores = Store.objects.order_by('display_order');
    store = stores.get(slug=store_slug);
    categories = store.categories.filter(parent__isnull=True).order_by('name')
  except ObjectDoesNotExist as e:
    return HttpResponse(e)

  # Build common context
  context = RequestContext(request, {
    'stores': stores,
    'store':store,
    'categories':categories,
  })

  return context

def items_for_store(store_slug):
  return Item.objects.filter(category__store__slug=store_slug)

def limit_to_page(queryset, page=1, per_page=ITEM_PER_PAGE):
  if type(page) is not int:
    try:
      page = int(page)
    except ValueError:
      page = 1
  return queryset[per_page * (page - 1) : per_page * page]

# Views

@csrf_exempt
def to_default(request):
  return HttpResponseRedirect('sobeys');

def store_home(request, store_slug):
  template = loader.get_template('shop/store_home.html')
  context = common_context(request, store_slug)
  return HttpResponse(template.render(context))

def store_category(request, store_slug, category_id=None):
  template = loader.get_template('shop/store_search.html')
  context = common_context(request, store_slug)

  # Fetch category for current selection
  if category_id is not None:
    try:
      category = Category.objects.get(id=category_id)
      context['category'] = category
      context['item_metas_filters'] = ItemMetaFilter.objects.meta_filters_for_items(category.items)
      context['query'] = request.GET.urlencode()
      context['query_dict'] = json.dumps(dict(request.GET.iterlists()))
    except ObjectDoesNotExist:
      return store_home(request, store_slug)

  return HttpResponse(template.render(context))

def store_search(request, store_slug, keyword=None):
  template = loader.get_template('shop/store_search.html')
  context = common_context(request, store_slug)

  # Add search_keyword to the context
  if keyword is not None:
    context['search_keyword'] = keyword

  return HttpResponse(template.render(context))

# APIs

def all_featured_items(request, featured_as, page=1):
  items = Item.objects.filter(featured=featured_as).order_by('name')
  items = limit_to_page(items, page, FEATURED_ITEM_PER_PAGE)

  return items_response(items)

def store_items(request, store_slug, category_id=None, keyword=None, page=1):
  items = items_for_store(store_slug).order_by('name')

  if category_id is not None and len(category_id) > 0:
    items = items.filter(category__id=category_id)

  if keyword is not None and len(keyword) > 0:
    items = items.filter(name__contains=keyword)

  filter = json.loads(request.GET.get('filter', '{}'))
  if len(filter) > 0:
    for key, options in filter.items():
      if len(options) > 0:
        item_ids = ItemMeta.objects.filter(key=key, value__in=options).values('item__id')
        items = items.filter(id__in=item_ids)

  items = limit_to_page(items, page, ITEM_PER_PAGE)

  return items_response(items)

def store_popular_items(request, store_slug, page=1):
  items = items_for_store(store_slug).order_by('-sold_number')
  items = limit_to_page(items, page, POPULAR_ITEM_PER_PAGE)

  return items_response(items)

def store_onsale_items(request, store_slug, page=1):
  items = items_for_store(store_slug).filter(on_sale=True).order_by('-sold_number')
  items = limit_to_page(items, page, ON_SALE_ITEM_PER_PAGE)

  return items_response(items)

def store_featured_items(request, store_slug, featured_as, page=1):
  items = items_for_store(store_slug).filter(featured=featured_as).order_by('name')
  items = limit_to_page(items, page, FEATURED_ITEM_PER_PAGE)

  return items_response(items)
