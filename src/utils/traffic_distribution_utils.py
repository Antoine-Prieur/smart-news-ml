def validate_traffic_distribution(
    traffic_distribution: list[float],
) -> None:
    """Validate that traffic distribution sums to 100%"""
    total_traffic = sum(
        traffic_percentage for traffic_percentage in traffic_distribution
    )
    if abs(total_traffic - 100.0) > 1e-6:
        raise ValueError(
            f"Total traffic distribution must equal 100, got {total_traffic}"
        )
