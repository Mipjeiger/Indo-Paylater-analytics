from feast import Entity, ValueType

# Define the borrower entity
borrower = Entity(
    name="borrower",
    join_keys=["borrower_id"],
    value_type=ValueType.STRING,
    description="Paylater borrower"
)