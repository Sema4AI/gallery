import json
import os
from datetime import datetime, timezone


def load_json_data(file_path):
    module_dir = os.path.dirname(__file__)
    full_path = os.path.join(module_dir, "data", file_path)
    with open(full_path, 'r') as file:
        return json.load(file)


def format_aggregation_value(value):
    return round(value, 2)


class WorkoutMetricsService:
    def __init__(self):
        self.data = {
            "workouts_indoor_run": load_json_data("workouts_indoor_run.json"),
            "workouts_outdoor_run": load_json_data("workouts_outdoor_run.json"),
            "workouts_run": load_json_data("workouts_run.json"),
            "workouts_indoor_cycling": load_json_data("workouts_indoor_cycling.json"),
            "workouts_outdoor_cycling": load_json_data("workouts_outdoor_cycling.json"),
            "workouts_cycling": load_json_data("workouts_cycling.json"),
            "workouts_indoor_walk": load_json_data("workouts_indoor_walk.json"),
            "workouts_outdoor_walk": load_json_data("workouts_outdoor_walk.json"),
            "workouts_walk": load_json_data("workouts_walk.json"),
            "workouts_hiking": load_json_data("workouts_hiking.json"),
            "workouts_tennis": load_json_data("workouts_tennis.json"),
            "workouts_core_training": load_json_data("workouts_core_training.json")
        }

    def aggregate_workout_metrics(self, metric, aggregation_type, start_date_str, end_date_str, collections):
        # Convert string dates to datetime objects with UTC timezone
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        results = []
        for collection_name in collections:
            workouts = self.data.get(collection_name, [])
            filtered_workouts = [w for w in workouts if
                                 'start' in w and start_date <= datetime.strptime(w['start'], "%Y-%m-%d %H:%M:%S %z") < end_date]

            values = []
            if metric == 'distance':
                values = [float(w['distance'].get('qty', 0)) for w in filtered_workouts if 'distance' in w]
            elif metric == 'duration':
                values = [float(w.get('duration', 0)) for w in filtered_workouts]
            elif metric == 'calorie':
                values = [float(w['activeEnergy'].get('qty', 0)) for w in filtered_workouts if 'activeEnergy' in w]
            elif metric == 'heartRate':
                # Averaging heart rate data for each workout
                for w in filtered_workouts:
                    if 'heartRateData' in w:
                        heart_rate_values = [hr['qty'] for hr in w['heartRateData'] if 'qty' in hr]
                        if heart_rate_values:
                            avg_heart_rate = sum(heart_rate_values) / len(heart_rate_values)
                            values.append(avg_heart_rate)
            elif metric == 'heartRateRecovery':
                # Collecting all heart rate recovery values
                for w in filtered_workouts:
                    if 'heartRateRecovery' in w:
                        values.extend([hr['qty'] for hr in w['heartRateRecovery'] if 'qty' in hr])

            result = 0
            if aggregation_type == 'sum':
                result = sum(values)
            elif aggregation_type == 'average':
                result = sum(values) / len(values) if values else 0
            elif aggregation_type == 'max':
                result = max(values) if values else 0
            elif aggregation_type == 'min':
                result = min(values) if values else 0
            elif aggregation_type == 'count':
                result = len(values)
            results.append(result)

        final_result = 0
        if aggregation_type in ['average', 'max', 'min']:
            if results:
                if aggregation_type == 'average':
                    final_result = sum(results) / len(results)
                elif aggregation_type == 'max':
                    final_result = max(results)
                elif aggregation_type == 'min':
                    final_result = min(results)
        else:
            final_result = sum(results)

        return format_aggregation_value(final_result)

    def get_performance(self, workout_type, metric, aggregation_type, start_date, end_date):
        collections_map = {
            'run': ['workouts_indoor_run', 'workouts_outdoor_run', 'workouts_run'],
            'cycle': ['workouts_indoor_cycling', 'workouts_outdoor_cycling', 'workouts_cycling'],
            'walk': ['workouts_indoor_walk', 'workouts_outdoor_walk', 'workouts_walk'],
            'hike': ['workouts_hiking'],
            'tennis': ['workouts_tennis'],
            'core': ['workouts_core_training']
        }
        if workout_type in collections_map:
            return self.aggregate_workout_metrics(metric, aggregation_type, start_date, end_date, collections_map[workout_type])
        else:
            return 0.0

    def get_last_n_run_workout_details(self, n):
        run_collections = ['workouts_indoor_run', 'workouts_outdoor_run', 'workouts_run']
        all_runs = []
        for collection in run_collections:
            all_runs.extend(self.data.get(collection, []))

        # Sort by start date
        all_runs.sort(key=lambda x: datetime.strptime(x['start'], "%Y-%m-%d %H:%M:%S %z"), reverse=True)
        last_n_runs = all_runs[:n]
        return json.dumps(last_n_runs, default=lambda x: x.isoformat() if isinstance(x, datetime) else x)
