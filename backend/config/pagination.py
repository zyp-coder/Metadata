from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """标准分页：默认每页 20 条，支持前端通过 page_size 覆盖（用于字段管理等需拉全量的场景）。

    - page_size：默认页大小
    - page_size_query_param：允许前端传 ?page_size=N 覆盖
    - max_page_size：单页上限，防止极端值拖垮服务
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100000
