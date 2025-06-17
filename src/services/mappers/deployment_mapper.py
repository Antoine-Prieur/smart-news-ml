from src.database.repositories.models.deployment_repository_models import (
    MLActiveDeploymentDocument,
    MLDeploymentDocument,
)
from src.services.models.deployment_models import MLActiveDeployment, MLDeployment


def db_to_domain_active_deployment(
    db_model: MLActiveDeploymentDocument,
) -> MLActiveDeployment:
    """Convert database active deployment document to domain model"""
    return MLActiveDeployment(
        predictor_id=db_model.predictor_id,
        traffic_percentage=db_model.traffic_percentage,
    )


def domain_to_db_active_deployment(
    domain_model: MLActiveDeployment,
) -> MLActiveDeploymentDocument:
    """Convert domain active deployment model to database document"""
    from bson import ObjectId

    return MLActiveDeploymentDocument(
        predictor_id=ObjectId(domain_model.predictor_id),
        traffic_percentage=domain_model.traffic_percentage,
    )


def db_to_domain_deployment(db_model: MLDeploymentDocument) -> MLDeployment:
    """Convert database document to domain model"""
    if db_model.id is None:
        raise ValueError("DB models should always have an ID")

    active_deployments = [
        db_to_domain_active_deployment(deployment)
        for deployment in db_model.active_deployments
    ]

    return MLDeployment(
        id=db_model.id,
        predictor_name=db_model.predictor_name,
        active_deployments=active_deployments,
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def domain_to_db_deployment(domain_model: MLDeployment) -> MLDeploymentDocument:
    """Convert domain model to database document"""
    from bson import ObjectId

    active_deployments = [
        domain_to_db_active_deployment(deployment)
        for deployment in domain_model.active_deployments
    ]

    return MLDeploymentDocument(
        _id=ObjectId(domain_model.id),
        predictor_name=domain_model.predictor_name,
        active_deployments=active_deployments,
        created_at=domain_model.created_at,
        updated_at=domain_model.updated_at,
    )
