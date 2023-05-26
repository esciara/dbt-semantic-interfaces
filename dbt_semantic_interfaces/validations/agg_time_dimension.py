from typing import Generic, List, Sequence

from dbt_semantic_interfaces.protocols.semantic_manifest import SemanticManifestT
from dbt_semantic_interfaces.protocols.semantic_model import SemanticModel
from dbt_semantic_interfaces.references import (
    SemanticModelElementReference,
    TimeDimensionReference,
)
from dbt_semantic_interfaces.type_enums.dimension_type import DimensionType
from dbt_semantic_interfaces.validations.validator_helpers import (
    FileContext,
    SemanticManifestValidationRule,
    SemanticModelElementContext,
    SemanticModelElementType,
    ValidationError,
    ValidationIssue,
    validate_safely,
)


class AggregationTimeDimensionRule(SemanticManifestValidationRule[SemanticManifestT], Generic[SemanticManifestT]):
    """Checks that the agg time dimension for a measure points to a valid time dimension in the semantic model."""

    @staticmethod
    @validate_safely(whats_being_done="checking aggregation time dimension for semantic models in the model")
    def validate_manifest(semantic_manifest: SemanticManifestT) -> Sequence[ValidationIssue]:  # noqa: D
        issues: List[ValidationIssue] = []
        for semantic_model in semantic_manifest.semantic_models:
            issues.extend(AggregationTimeDimensionRule._validate_semantic_model(semantic_model))

        return issues

    @staticmethod
    def _time_dimension_in_model(
        time_dimension_reference: TimeDimensionReference, semantic_model: SemanticModel
    ) -> bool:
        for dimension in semantic_model.dimensions:
            if dimension.type == DimensionType.TIME and dimension.name == time_dimension_reference.element_name:
                return True
        return False

    @staticmethod
    @validate_safely(whats_being_done="checking aggregation time dimension for a semantic model")
    def _validate_semantic_model(semantic_model: SemanticModel) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        for measure in semantic_model.measures:
            measure_context = SemanticModelElementContext(
                file_context=FileContext.from_metadata(metadata=semantic_model.metadata),
                semantic_model_element=SemanticModelElementReference(
                    semantic_model_name=semantic_model.name, element_name=measure.name
                ),
                element_type=SemanticModelElementType.MEASURE,
            )
            agg_time_dimension_reference = measure.checked_agg_time_dimension
            if not AggregationTimeDimensionRule._time_dimension_in_model(
                time_dimension_reference=agg_time_dimension_reference, semantic_model=semantic_model
            ):
                issues.append(
                    ValidationError(
                        context=measure_context,
                        message=f"In semantic model '{semantic_model.name}', measure '{measure.name}' has the "
                        f"aggregation time dimension set to '{agg_time_dimension_reference.element_name}', "
                        f"which is not a valid time dimension in the semantic model",
                    )
                )

        return issues
