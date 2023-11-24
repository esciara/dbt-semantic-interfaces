from __future__ import annotations

from typing import Callable, Generator, List, Tuple

from typing_extensions import Self

from dbt_semantic_interfaces.call_parameter_sets import (
    FilterCallParameterSets,
    ParseWhereFilterException,
)
from dbt_semantic_interfaces.implementations.base import (
    HashableBaseModel,
    PydanticCustomInputParser,
    PydanticParseableValueType,
)
from dbt_semantic_interfaces.parsing.where_filter.where_filter_parser import (
    WhereFilterParser,
)
from dbt_semantic_interfaces.pretty_print import pformat_big_objects


class PydanticWhereFilter(PydanticCustomInputParser, HashableBaseModel):
    """Pydantic implementation of a WhereFilter.

    This specifies a templated SQl where expression, with templates allowing for extraction of dimensions and
    entities (and, eventually, measures and metrics) to include in the filter itself. This filter will then
    be applied to an input data set, either from an original input source or an intermediate subquery output.

    The data set will contain entities and dimensions as referenced in the query along with the entities and dimensions
    that are referenced in any of these filters, whether they are part of the query request or metric definition.
    """

    # The where_sql_template field is used in PydanticWhereFilterIntersection.convert_legacy_input. Remove with caution.
    where_sql_template: str

    @classmethod
    def _from_yaml_value(
        cls,
        input: PydanticParseableValueType,
    ) -> PydanticWhereFilter:
        """Parses a WhereFilter from a string found in a user-provided model specification.

        User-provided constraint strings are SQL snippets conforming to the expectations of SQL WHERE clauses,
        and as such we parse them using our standard parse method below.
        """
        if isinstance(input, str):
            return PydanticWhereFilter(where_sql_template=input)
        else:
            raise ValueError(f"Expected input to be of type string, but got type {type(input)} with value: {input}")

    @property
    def call_parameter_sets(self) -> FilterCallParameterSets:  # noqa: D
        return WhereFilterParser.parse_call_parameter_sets(self.where_sql_template)


class PydanticWhereFilterIntersection(HashableBaseModel):
    """Pydantic implementation of a WhereFilterIntersection."""

    # This class can not have a property named `where_sql_template` without a parsing logic update
    __WHERE_SQL_TEMPLATE_FIELD__ = "where_sql_template"
    __WHERE_FILTERS_FIELD__ = "where_filters"

    where_filters: List[PydanticWhereFilter]

    @classmethod
    def __get_validators__(cls) -> Generator[Callable[[PydanticParseableValueType], Self], None, None]:
        """Pydantic magic method for allowing handling of arbitrary input on model_validate invocation.

        This class requires more subtle handling of input deserialized object types (dicts), and so it cannot
        extend the common interface via _from_yaml_values.
        """
        yield cls._convert_legacy_and_yaml_input

    @classmethod
    def _convert_legacy_and_yaml_input(cls, input: PydanticParseableValueType) -> Self:
        """Specifies raw input conversion rules to ensure serialized semantic manifests will parse correctly.

        The original spec for where filters relied on a raw WhereFilter object, but this has now been updated to
        expect an object containing a collection of WhereFilters.

        The inputs for the original PydanticWhereFilter could have been either a bare string, a PydanticWhereFilter,
        or a partially deserialized json object (i.e., dict) representation of the PydanticWhereFilter.

        Consequently, we must support a variety of inputs and coerce them into the appropriate form, which is in general
        a List[valid_where_filter_input] with valid_where_filter_input being one of the types described above. Here
        are the operations:

        Sequence transforms:
        1. str -> {"where_filters": [input]}
        2. PydanticWhereFilter -> {"where_filters": [input]}
        3. {"where_sql_template": str} -> {"where_filters": [input]}

        Object initializations (inputs requiring standard initialization, validated via the next pydantic operation):
        1. List -> PydanticWhereFilterIntersection(where_filters=input)
        2. other dicts -> PydanticWhereFilterIntersection(**input)

        Identity transforms (no-ops, as these represent PydanticWhereFilterIntersection objects):
        1. PydanticWhereFilterIntersection
        """
        has_legacy_keys = isinstance(input, dict) and cls.__WHERE_SQL_TEMPLATE_FIELD__ in input.keys()
        is_legacy_where_filter = isinstance(input, str) or isinstance(input, PydanticWhereFilter) or has_legacy_keys

        if is_legacy_where_filter:
            return cls(where_filters=[input])
        elif isinstance(input, list):
            return cls(where_filters=input)
        elif isinstance(input, dict):
            return cls(**input)
        elif isinstance(input, cls):
            return input
        else:
            raise ValueError(
                f"Expected input to be of type string, list, PydanticWhereFilter, PydanticWhereFilterIntersection, "
                f"or dict but got {type(input)} with value {input}"
            )

    @property
    def filter_expression_parameter_sets(self) -> List[Tuple[str, FilterCallParameterSets]]:
        """Gets the call parameter sets for each filter expression."""
        filter_parameter_sets: List[Tuple[str, FilterCallParameterSets]] = []
        invalid_filter_expressions: List[Tuple[str, Exception]] = []
        for where_filter in self.where_filters:
            try:
                filter_parameter_sets.append((where_filter.where_sql_template, where_filter.call_parameter_sets))
            except Exception as e:
                invalid_filter_expressions.append((where_filter.where_sql_template, e))

        if invalid_filter_expressions:
            raise ParseWhereFilterException(
                f"Encountered one or more errors when parsing the set of filter expressions "
                f"{pformat_big_objects(self.where_filters)}! Invalid expressions: \n "
                f"{pformat_big_objects(invalid_filter_expressions)}"
            )

        return filter_parameter_sets
