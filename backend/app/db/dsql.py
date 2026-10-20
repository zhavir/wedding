"""Async bridge for the AWS DSQL dialect, which currently exposes sync drivers."""

from functools import lru_cache

from aurora_dsql_sqlalchemy.psycopg import AuroraDSQLDialect_psycopg
from sqlalchemy.dialects import registry
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.dialects.postgresql.psycopg import PGDialectAsync_psycopg


class AuroraDSQLAsyncDialect(PGDialectAsync_psycopg, AuroraDSQLDialect_psycopg):
    """Keep AWS's DSQL compiler/reflection and SQLAlchemy's async psycopg adapter."""

    supports_statement_cache = True

    @classmethod
    def get_async_dialect_cls(cls, url):
        # The inherited psycopg hook otherwise substitutes plain PostgreSQL.
        return cls

    @lru_cache  # noqa: B019 -- bounded cache, matching the upstream reflection method
    def _columns_query(self, schema, has_filter_names, scope, kind):
        query = super()._columns_query(schema, has_filter_names, scope, kind)
        if "collation" not in query.selected_columns:
            # SQLAlchemy 2.1's reflection reader requires this field; the AWS
            # adapter still builds the older query. Preserve its DSQL query
            # and add SQLAlchemy's correlated collation expression.
            postgres_query = PGDialect._columns_query(self, schema, has_filter_names, scope, kind)
            query = query.add_columns(postgres_query.selected_columns.collation)
        return query

    def do_execute(self, cursor, statement, parameters, context=None):
        cursor.execute(statement, parameters)
        if context and context.isddl:
            # Async adapted cursors have no .connection; commit through the
            # SQLAlchemy connection proxy so psycopg's coroutine is awaited.
            context.root_connection.connection.commit()

    def do_execute_no_params(self, cursor, statement, context=None):
        cursor.execute(statement)
        if context and context.isddl:
            context.root_connection.connection.commit()


registry.register("auroradsql.psycopg_async", __name__, "AuroraDSQLAsyncDialect")
