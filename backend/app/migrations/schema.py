"""Schema comparison shared by Alembic autogenerate and migration regressions."""

from sqlalchemy import literal


def compare_server_default(
    context, inspected_column, metadata_column, inspected, metadata, rendered
):
    if context.dialect.name != "sqlite":
        return None

    # SQLite reflects an empty-string default as (''); its parentheses do not
    # change the SQL literal. Preserve quotes so distinct values still differ.
    def normalize(value):
        while value is not None and value.startswith("(") and value.endswith(")"):
            value = value[1:-1].strip()
        return value

    if metadata is not None and isinstance(metadata.arg, str):
        rendered = str(
            literal(metadata.arg).compile(
                dialect=context.dialect, compile_kwargs={"literal_binds": True}
            )
        )
    return normalize(inspected) != normalize(rendered)
