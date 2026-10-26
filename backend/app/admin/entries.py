from typing import cast

from sqladmin import ModelView
from sqladmin._types import SimpleColumnFilter
from sqladmin.filters import OperationColumnFilter


class EntryAdmin(ModelView):
    details_template = "admin/details.html"
    edit_template = "admin/edit.html"

    async def entry_navigation(self, request, model, route):
        """Use the list's ordering, with a stable ID tie-breaker, across pages."""
        key = self.pk_columns[0]
        query = self.list_query(request).with_only_columns(key, maintain_column_froms=True)
        for filter_ in self.get_filters():
            value = request.query_params.get(filter_.parameter_name)
            if not value:
                continue
            if isinstance(filter_, OperationColumnFilter):
                operation = request.query_params.get(f"{filter_.parameter_name}_op")
                if operation:
                    query = await filter_.get_filtered_query(query, operation, value, self.model)
                continue
            query = await cast(SimpleColumnFilter, filter_).get_filtered_query(
                query, value, self.model
            )
        if search := request.query_params.get("search"):
            query = self.search_query(query, search)
        query = self.sort_query(query, request).order_by(key)
        async with self.session_maker() as db:
            ids = list(await db.scalars(query))
        if model.id not in ids:
            return None, None
        position = ids.index(model.id)

        def url(index):
            if not 0 <= index < len(ids):
                return None
            return request.url_for(route, identity=self.identity, pk=ids[index]).replace(
                query=request.url.query
            )

        return url(position - 1), url(position + 1)
