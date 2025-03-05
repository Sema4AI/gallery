from sema4ai.actions import Response, action
from workout_metrics_service import WorkoutMetricsService

workout_metrics_service = WorkoutMetricsService()


@action(is_consequential=False)
def get_run_workout_performance(
    metric: str, aggregation_type: str, start_date: str, end_date: str
) -> Response[float]:
    """
    Calculate various running performance metrics within a specified time period across different running workouts.

    Args:
        metric (str): The running performance metric to aggregate. Supported metrics include 'distance', 'duration', 'heartRate','heartRateRecovery' and 'calorie'.
        aggregation_type (str): Type of aggregation to perform. Supported types are 'sum', 'average', 'max', 'min', and 'count'.
        start_date (str): The start date for data aggregation in 'YYYY-MM-DD' format.
        end_date (str): The end date for data aggregation in 'YYYY-MM-DD' format.

    Returns:
        float: The result of the specified aggregation on the running metric.

    Description:
        This function aggregates running performance data based on the specified metric and aggregation type
        within a given date range.

    Examples:
        - To calculate the total running distance for January 2023, call
        get_run_workout_performance('distance', 'sum', '2023-01-01', '2023-02-01').
        - To find out the average heart rate during runs in 2023, use
        get_run_workout_performance('heartRate', 'average', '2023-01-01', '2024-01-01').
        - To find out the total calorie burned during runs in 2023, use
        get_run_workout_performance('calorie', 'sum', '2023-01-01', '2024-01-01').

    """
    return Response(
        result=workout_metrics_service.get_performance(
            "run", metric, aggregation_type, start_date, end_date
        )
    )


@action(is_consequential=False)
def get_cycle_workout_performance(
    metric: str, aggregation_type: str, start_date: str, end_date: str
) -> Response[float]:
    """
    Calculate various cycling performance metrics within a specified time period across different cycling workouts.

    Args:
        metric (str): The running performance metric to aggregate. Supported metrics include 'distance', 'duration', 'heartRate', 'heartRateRecovery' and 'calorie'.
        aggregation_type (str): Type of aggregation to perform. Supported types are 'sum', 'average', 'max', 'min',and 'count'.
        start_date (str): The start date for data aggregation in 'YYYY-MM-DD' format.
        end_date (str): The end date for data aggregation in 'YYYY-MM-DD' format.

    Returns:
        float: The result of the specified aggregation on the cycling metric.

    Description:
        This function aggregates cycling performance data based on the specified metric and aggregation type
        within a given date range.

    Examples:
        - To calculate the total cyling distance for January 2023, call
        get_cycle_workout_performance('distance', 'sum', '2023-01-01', '2023-02-01').
        - To find out the average heart rate during cycling in 2023, use
        get_cycle_workout_performance('heartRate', 'average', '2023-01-01', '2024-01-01').
        - To find out the total calorie burned during cycling in 2023, use
        get_cycle_workout_performance('calorie', 'sum', '2023-01-01', '2024-01-01').


    """
    return Response(
        result=workout_metrics_service.get_performance(
            "cycle", metric, aggregation_type, start_date, end_date
        )
    )


@action(is_consequential=False)
def get_walk_workout_performance(
    metric: str, aggregation_type: str, start_date: str, end_date: str
) -> Response[float]:
    """
    Calculate various walking performance metrics within a specified time period across different walking workouts.

    Args:
        metric (str): The running performance metric to aggregate. Supported metrics include 'distance', 'duration','heartRate', 'heartRateRecovery' and 'calorie'.
        aggregation_type (str): Type of aggregation to perform. Supported types are 'sum', 'average', 'max', 'min',and 'count'.
        start_date (str): The start date for data aggregation in 'YYYY-MM-DD' format.
        end_date (str): The end date for data aggregation in 'YYYY-MM-DD' format.

    Returns:
        float: The result of the specified aggregation on the walking metric.

    Description:
        This function aggregates walking performance data based on the specified metric and aggregation type
        within a given date range.

    Examples:
        - To calculate the total walking distance for January 2023, call
        get_walk_workout_performance('distance', 'sum', '2023-01-01', '2023-02-01' ).
        - To find out the average heart rate during walking in 2023, use
        get_walk_workout_performance('heartRate', 'average', '2023-01-01', '2024-01-01').
        - To find out the total calorie burned during walking in 2023, use
        get_walk_workout_performance('calorie', 'sum', '2023-01-01', '2024-01-01').

    """
    return Response(
        result=workout_metrics_service.get_performance(
            "walk", metric, aggregation_type, start_date, end_date
        )
    )


@action(is_consequential=False)
def get_hike_workout_performance(
    metric: str, aggregation_type: str, start_date: str, end_date: str
) -> Response[float]:
    """
    Calculate various hiking performance metrics within a specified time period across different hiking workouts.

    Args:
        metric (str): The running performance metric to aggregate. Supported metrics include 'distance', 'duration','heartRate', 'heartRateRecovery' and 'calorie'.
        aggregation_type (str): Type of aggregation to perform. Supported types are 'sum', 'average', 'max', 'min', and 'count'.
        start_date (str): The start date for data aggregation in 'YYYY-MM-DD' format.
        end_date (str): The end date for data aggregation in 'YYYY-MM-DD' format.

    Returns:
        float: The result of the specified aggregation on the hiking metric.

    Description:
        This function aggregates hiking performance data based on the specified metric and aggregation type
        within a given date range.

    Examples:
        - To calculate the total hiking distance for January 2023, call
        get_hike_workout_performance('distance', 'sum', '2023-01-01', '2023-02-01' ).
        - To find out the average heart rate during hiking in 2023, use
        get_hike_workout_performance('heartRate', 'average', '2023-01-01', '2024-01-01').
        - To find out the total calorie burned during hiking in 2023, use
        get_hike_workout_performance('calorie', 'sum', '2023-01-01', '2024-01-01').
    """
    return Response(
        result=workout_metrics_service.get_performance(
            "hike", metric, aggregation_type, start_date, end_date
        )
    )


@action(is_consequential=False)
def get_tennis_workout_performance(
    metric: str, aggregation_type: str, start_date: str, end_date: str
) -> Response[float]:
    """
    Calculate various tennis performance metrics within a specified time period across different tennis workouts.

    Args:
        metric (str): The running performance metric to aggregate. Supported metrics include 'distance', 'duration', 'heartRate', 'heartRateRecovery' and 'calorie'.
        aggregation_type (str): Type of aggregation to perform. Supported types are 'sum', 'average', 'max', 'min', and 'count'.
        start_date (str): The start date for data aggregation in 'YYYY-MM-DD' format.
        end_date (str): The end date for data aggregation in 'YYYY-MM-DD' format.

    Returns:
        float: The result of the specified aggregation on the tennis metric.

    Description:
        This function aggregates tennis performance data based on the specified metric and aggregation type
        within a given date range.

    Examples:
        - To calculate the total tennis distance for January 2023, call
        get_tennis_workout_performance('distance', 'sum', '2023-01-01', '2023-02-01' ).
        - To find out the average heart rate during tennis in 2023, use
        get_tennis_workout_performance('heartRate', 'average', '2023-01-01', '2024-01-01').
        - To find out the total calorie burned during tennis in 2023, use
        get_tennis_workout_performance('calorie', 'sum', '2023-01-01', '2024-01-01').
    """
    return Response(
        result=workout_metrics_service.get_performance(
            "tennis", metric, aggregation_type, start_date, end_date
        )
    )


@action(is_consequential=False)
def get_core_workout_performance(
    metric: str, aggregation_type: str, start_date: str, end_date: str
) -> Response[float]:
    """
    Calculate various core performance metrics within a specified time period across different core workouts.

    Args:
        metric (str): The running performance metric to aggregate. Supported metrics include 'distance', 'duration', 'heartRate', 'heartRateRecovery' and 'calorie'.
        aggregation_type (str): Type of aggregation to perform. Supported types are 'sum', 'average', 'max', 'min', and 'count'.
        start_date (str): The start date for data aggregation in 'YYYY-MM-DD' format.
        end_date (str): The end date for data aggregation in 'YYYY-MM-DD' format.

    Returns:
        float: The result of the specified aggregation on the core metric.

    Description:
        This function aggregates core performance data based on the specified metric and aggregation type
        within a given date range.

    Examples:
        - To calculate the total core distance for January 2023, call
        get_core_workout_performance('distance', 'sum', '2023-01-01', '2023-02-01' ).
        - To find out the average heart rate during core workouts in 2023, use
        get_core_workout_performance('heartRate', 'average', '2023-01-01', '2024-01-01').
        - To find out the total calorie burned during core workouts in 2023, use
        get_core_workout_performance('calorie', 'sum', '2023-01-01', '2024-01-01').

    """
    return Response(
        result=workout_metrics_service.get_performance(
            "core", metric, aggregation_type, start_date, end_date
        )
    )


# @action(is_consequential=False)
def get_last_n_run_workout_details(n: int) -> str:
    """
    Retrieves detailed information for the last 'n' run workouts, focusing on key metrics that
    quantify workout intensity, duration, and performance. This function is ideal for analyzing recent running  activity trends

    Args:
        n (int): The number of recent run workouts to retrieve, with '1' being the most recent.

    Returns:
        str: A JSON string containing a list of dictionaries, each detailing a run workout. Fields include:
            - start (datetime): Workout start time, in ISO format.
            - end (datetime): Workout end time, in ISO format.
            - duration (int): Total workout duration, in minutes.
            - distance.qty (float): Distance covered, in kilometers (km).
            - avgHeartRate (int): Average heart rate during the workout, in beats per minute (bpm).
            - maxHeartRate (int): Peak heart rate reached, in beats per minute (bpm).
            - activeEnergy.qty (float): Calories expended during the workout, in kilocalories (kcal).

    Examples:
        Retrieve details for the last 3 run workouts:
            json_string = get_last_n_run_workout_details(3)
    """
    return workout_metrics_service.get_last_n_run_workout_details(n)
