import copy

import pytest

from dbt_semantic_interfaces.implementations.metric import (
    MetricType,
    PydanticMetricInput,
    PydanticMetricTypeParams,
)
from dbt_semantic_interfaces.implementations.semantic_manifest import (
    PydanticSemanticManifest,
)
from dbt_semantic_interfaces.model_validator import ModelValidator
from dbt_semantic_interfaces.test_utils import metric_with_guaranteed_meta
from dbt_semantic_interfaces.validations.metrics import DerivedMetricRule


def test_can_configure_model_validator_rules(  # noqa: D
    simple_semantic_manifest__with_primary_transforms: PydanticSemanticManifest,
) -> None:
    model = copy.deepcopy(simple_semantic_manifest__with_primary_transforms)
    model.metrics.append(
        metric_with_guaranteed_meta(
            name="metric_doesnt_exist_squared",
            type=MetricType.DERIVED,
            type_params=PydanticMetricTypeParams(
                expr="metric_doesnt_exist * metric_doesnt_exist",
                metrics=[PydanticMetricInput(name="metric_doesnt_exist")],
            ),
        )
    )

    # confirm that with the default configuration, an issue is raised
    issues = ModelValidator().validate_model(model)
    assert len(issues.all_issues) == 1, f"ModelValidator with default rules had unexpected number of issues {issues}"

    # confirm that a custom configuration excluding ValidMaterializationRule, no issue is raised
    rules = [rule for rule in ModelValidator.DEFAULT_RULES if rule.__class__ is not DerivedMetricRule]
    issues = ModelValidator(rules=rules).validate_model(model)
    assert len(issues.all_issues) == 0, f"ModelValidator without DerivedMetricRule returned issues {issues}"


def test_cant_configure_model_validator_without_rules() -> None:  # noqa: D
    with pytest.raises(ValueError):
        ModelValidator(rules=[])

    with pytest.raises(ValueError):
        ModelValidator(rules=())

    with pytest.raises(ValueError):
        ModelValidator(rules=None)  # type: ignore
