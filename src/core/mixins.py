from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import operator
from functools import reduce

class EnhancedListMixin:
    """
    A reusable mixin for Django Class-Based Views (ListView) to provide:
    - Advanced Filtering (via django-filter)
    - Multi-field Search
    - Custom Sorting/Ordering
    - Configurable Pagination
    """
    filterset_class = None
    search_fields = []  # List of fields to search in (e.g., ['name', 'student__user__first_name'])
    ordering_fields = [] # List of allowed fields for sorting
    default_ordering = '-created_at'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        # 1. Apply Filtering (django-filter)
        if self.filterset_class:
            self.filterset = self.filterset_class(self.request.GET, queryset=queryset)
            queryset = self.filterset.qs

        # 2. Apply Searching
        search_query = self.request.GET.get('q')
        if search_query and self.search_fields:
            search_filters = [Q(**{f"{field}__icontains": search_query}) for field in self.search_fields]
            queryset = queryset.filter(reduce(operator.or_, search_filters))

        # 3. Apply Sorting
        ordering = self.request.GET.get('sort', self.default_ordering)
        if ordering:
            # Validate ordering field (handle descending '-' prefix)
            clean_ordering = ordering.lstrip('-')
            if self.ordering_fields and clean_ordering in self.ordering_fields:
                queryset = queryset.order_by(ordering)
            elif not self.ordering_fields: # If not specified, allow any field (not recommended for production but flexible)
                queryset = queryset.order_by(ordering)
            else:
                queryset = queryset.order_by(self.default_ordering)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filterset to context for rendering forms
        if self.filterset_class:
            context['filterset'] = self.filterset
            
        # Preserve query parameters for pagination links
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_params'] = query_params.urlencode()
        
        # Current sort and search
        context['current_sort'] = self.request.GET.get('sort', self.default_ordering)
        context['current_search'] = self.request.GET.get('q', '')
        
        return context
