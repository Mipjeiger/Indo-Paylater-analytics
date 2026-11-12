"""Register trained models in the registry.

Stub implementation – stores model metadata in the PostgreSQL registry table.
"""

def register_model(task_name: str, model, version: str, metrics: dict):
    # TODO: Insert into paylater.model_versions using SQLAlchemy
    raise NotImplementedError("Model registration not implemented yet")
