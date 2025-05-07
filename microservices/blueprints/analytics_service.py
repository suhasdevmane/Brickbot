# blueprints/analytics_module.py
from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
import logging
import json

analytics_service = Blueprint("analytics_service", __name__)

def analyze_recalibration_frequency(sensor_data):
    """
    Analyzes recalibration frequency for sensors given timeseries data.

    Expected input format (as a Python dict or JSON string):
    {
        "timeseriesId_1": [
            {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
            ...
        ],
        "timeseriesId_2": [
            {"datetime": "2025-02-10 06:00:00", "reading_value": 28.10},
            ...
        ],
        ...
    }

    For each timeseries ID, it calculates the mean and standard deviation of the reading_value,
    computes the coefficient of variation (cv = std / mean), and then:
      - If cv > 0.1, indicates high variability (suggesting more frequent recalibration).
      - Otherwise, indicates stable performance.

    Returns:
      A dictionary where each timeseries ID maps to its analysis results.
    """
    # If sensor_data is a JSON string, convert it into a dictionary.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    response = {}
    # Iterate over each timeseries ID.
    for timeseries_id, readings in sensor_data.items():
        if not readings:
            response[timeseries_id] = {"message": "No data available"}
            continue

        try:
            df = pd.DataFrame(readings)
            # Rename "datetime" column to "timestamp" if it exists.
            if "datetime" in df.columns:
                df = df.rename(columns={"datetime": "timestamp"})
            # Convert the timestamp column to datetime objects.
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Compute mean and standard deviation of the reading values.
            mean_val = df["reading_value"].mean()
            std_val = df["reading_value"].std() or 0.0
            cv = std_val / mean_val if mean_val else 0

            if cv > 0.1:
                response[timeseries_id] = {
                    "mean": round(mean_val, 4),
                    "std": round(std_val, 4),
                    "coefficient_of_variation": round(cv, 4),
                    "message": f"Timeseries {timeseries_id} has high variability; recalibration might be required more frequently."
                }
            else:
                response[timeseries_id] = {
                    "mean": round(mean_val, 4),
                    "std": round(std_val, 4),
                    "coefficient_of_variation": round(cv, 4),
                    "message": f"Timeseries {timeseries_id} performance is stable; no immediate recalibration needed."
                }

        except Exception as e:
            logging.error(f"Data conversion error for timeseries {timeseries_id}: {e}")
            response[timeseries_id] = {"error": "Invalid sensor data format"}

    if not response:
        return {"message": "No timeseries data available."}

    return response

def analyze_failure_trends(sensor_data):
    """
    Analyzes failure trends from grouped sensor data with a nested structure.

    Expected input format:
      {
          "1": {
              "Air_Temperature_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                      ...
                  ]
              },
              "Zone_Air_Humidity_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:35:00", "reading_value": 28.05},
                      ...
                  ]
              }
          },
          "2": {
              "Air_Temperature_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 06:00:00", "reading_value": 28.10},
                      ...
                  ]
              },
              "Zone_Air_Humidity_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 06:05:00", "reading_value": 29.00},
                      ...
                  ]
              }
          }
      }

    For each sensor type:
      - Converts the list of readings into a DataFrame.
      - Renames the "datetime" column to "timestamp" and converts it to datetime objects.
      - Filters for readings from the last 24 hours.
      - Computes a rolling average and rolling standard deviation (window of 5).
      - Computes the overall (baseline) standard deviation.
      - Compares the latest rolling standard deviation against 1.5× the baseline.
      - Flags the sensor if the latest rolling std exceeds that threshold.

    Returns:
      A nested dictionary where each sensor ID maps to sensor type keys with their analysis summary.
    """
    # Parse JSON string input if needed
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    response = {}
    now = pd.Timestamp.now()

    # Iterate over each sensor ID
    for sensor_id, sensor_types in sensor_data.items():
        response[sensor_id] = {}
        # Iterate over each sensor type for the given sensor ID
        for sensor_type, sensor_info in sensor_types.items():
            # Get the list of readings from the "timeseries_data" key
            timeseries_data = sensor_info.get("timeseries_data", [])
            try:
                df = pd.DataFrame(timeseries_data)
                # Rename "datetime" column to "timestamp" if it exists
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            except Exception as e:
                logging.error(
                    f"Data conversion error for sensor {sensor_id}, type {sensor_type}: {e}"
                )
                response[sensor_id][sensor_type] = {
                    "error": "Invalid sensor data format"
                }
                continue

            # Filter for readings in the last 24 hours
            sensor_df = df[df["timestamp"] >= now - pd.Timedelta(hours=24)]
            if sensor_df.empty:
                response[sensor_id][sensor_type] = {
                    "message": "No recent data available."
                }
                continue

            # Sort by timestamp and compute rolling statistics
            sensor_df = sensor_df.sort_values(by="timestamp")
            sensor_df["rolling_avg"] = (
                sensor_df["reading_value"].rolling(window=5, min_periods=1).mean()
            )
            sensor_df["rolling_std"] = (
                sensor_df["reading_value"].rolling(window=5, min_periods=1).std()
            )

            # Compute baseline standard deviation and latest rolling standard deviation
            baseline_std = sensor_df["reading_value"].std() or 0.0
            current_std = sensor_df["rolling_std"].iloc[-1] or 0.0

            # Compare current rolling std with 1.5 times the baseline
            if baseline_std > 0 and current_std > 1.5 * baseline_std:
                response[sensor_id][sensor_type] = {
                    "historical_mean": sensor_df["reading_value"].mean(),
                    "historical_std": baseline_std,
                    "latest_rolling_std": current_std,
                    "message": f"Sensor {sensor_id} ({sensor_type}) shows increased variance suggesting potential failure.",
                }
            else:
                response[sensor_id][sensor_type] = {
                    "historical_mean": sensor_df["reading_value"].mean(),
                    "historical_std": baseline_std,
                    "latest_rolling_std": current_std,
                    "message": f"Sensor {sensor_id} ({sensor_type}) readings are within normal range.",
                }
    if not response:
        return {
            "message": "No sensor data available for analysis in the last 24 hours."
        }

    return response


def analyze_device_deviation(sensor_data):
    """
    Analyzes deviation for each sensor in a JSON structure.

    Input format:
    {
        "timeseriesId_1": [
            {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
            ...
        ],
        "timeseriesId_2": [
            {"datetime": "2025-02-10 06:00:00", "reading_value": 28.10},
            ...
        ],
        ...
    }

    For each timeseries, it:
      - Calculates historical mean, std deviation.
      - Finds latest reading.
      - Flags if latest reading deviates beyond 2 standard deviations.

    Returns:
        A dict with analysis results for each timeseries.
    """
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing JSON: {e}")
            return {"error": "Invalid JSON"}

    response = {}

    for timeseries_id, readings in sensor_data.items():
        if not readings:
            response[timeseries_id] = {"message": "No data available"}
            continue

        try:
            df = pd.DataFrame(readings)
            if "datetime" in df.columns:
                df.rename(columns={"datetime": "timestamp"}, inplace=True)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.sort_values("timestamp", inplace=True)

            historical_mean = float(df["reading_value"].mean())
            historical_std = float(df["reading_value"].std() or 0.0)
            latest_reading = float(df.iloc[-1]["reading_value"])

            deviation_flag = False
            if historical_std > 0 and (
                latest_reading < historical_mean - 2 * historical_std
                or latest_reading > historical_mean + 2 * historical_std
            ):
                deviation_flag = True

            response[timeseries_id] = {
                "historical_mean": round(historical_mean, 4),
                "historical_std": round(historical_std, 4),
                "latest_reading": round(latest_reading, 4),
                "message": (
                    f"Deviation detected beyond 2 STD."
                    if deviation_flag
                    else "Within normal range."
                ),
            }

        except Exception as e:
            logging.error(f"Processing error for timeseries {timeseries_id}: {e}")
            response[timeseries_id] = {"error": "Processing failed"}

    return response


def analyze_sensor_status(sensor_data):
    """
    Analyzes the status of sensors based on their latest reporting timestamp.

    Expected input (nested format):
      {
          "1": {
              "Air_Temperature_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 27.99},
                      ...
                  ]
              },
              "Zone_Air_Humidity_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:35:00", "reading_value": 28.05},
                      {"datetime": "2025-02-10 05:35:12", "reading_value": 28.07},
                      ...
                  ]
              }
          },
          "2": {
              ...
          }
      }

    For each sensor type:
      - Converts the "timeseries_data" into a DataFrame.
      - Renames the "datetime" column to "timestamp" (if necessary) and converts it to datetime objects.
      - Finds the latest timestamp.
      - If the latest report is older than 1 hour from now, marks the sensor as "offline"; otherwise "online".

    Returns:
      A nested dictionary where each sensor ID maps to sensor type keys with their analysis, including:
        - last_report: the most recent report time as a string.
        - status: "online" or "offline".
        - message: a descriptive message.
    """
    # If sensor_data is a JSON string, convert it to a dictionary.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # If sensor_data is a list, assume it's data for a single sensor and wrap it in a dictionary.
    if isinstance(sensor_data, list):
        sensor_data = {"1": sensor_data}

    response = {}
    now = pd.Timestamp.now()
    threshold = now - pd.Timedelta(hours=1)

    # Process data for each sensor ID.
    for sensor_id, sensor_types in sensor_data.items():
        response[sensor_id] = {}
        # Process each sensor type for the current sensor ID.
        for sensor_type, sensor_info in sensor_types.items():
            # Extract the list of readings from the "timeseries_data" key.
            timeseries_data = sensor_info.get("timeseries_data", [])
            try:
                df = pd.DataFrame(timeseries_data)
                # Rename "datetime" to "timestamp" if it exists.
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            except Exception as e:
                logging.error(
                    f"Data conversion error for sensor {sensor_id}, type {sensor_type}: {e}"
                )
                response[sensor_id][sensor_type] = {
                    "error": "Invalid sensor data format"
                }
                continue

            # Find the most recent timestamp for the sensor type.
            last_report = df["timestamp"].max()
            if pd.isna(last_report) or last_report < threshold:
                status = "offline"
                message = f"Sensor {sensor_id} ({sensor_type}) appears offline or not reporting recently."
            else:
                status = "online"
                message = f"Sensor {sensor_id} ({sensor_type}) is reporting data normally. Last report at {last_report.strftime('%Y-%m-%d %H:%M:%S')}."

            response[sensor_id][sensor_type] = {
                "last_report": (
                    last_report.strftime("%Y-%m-%d %H:%M:%S")
                    if not pd.isna(last_report)
                    else None
                ),
                "status": status,
                "message": message,
            }

    if not response:
        return {"message": "No sensor data available for analysis."}

    return response


def analyze_air_quality_trends(sensor_data, target_sensor="Air_Quality_Sensor"):
    """
    Analyzes air quality (or specified target sensor) trends from nested sensor data.

    Expected input (as Python dict or JSON string):
      {
          "1": {
              "Air_Quality_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 80},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 78},
                      ...
                  ]
              },
              ...
          },
          "2": {
              "Air_Quality_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 06:00:00", "reading_value": 85},
                      ...
                  ]
              },
              ...
          }
      }

    For each sensor ID and the target sensor:
      - Computes mean (norm), latest reading, and determines trend: "rising", "falling", or "stable".

    Parameters:
        sensor_data: JSON or dict
        target_sensor: the sensor to analyze trends for (default: Air_Quality_Sensor)

    Returns:
        A nested dict mapping each sensor ID to its air quality trend analysis.
    """

    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing JSON: {e}")
            return {"error": "Invalid JSON"}

    response = {}

    for sensor_id, sensor_types in sensor_data.items():
        if target_sensor not in sensor_types:
            response[sensor_id] = {
                target_sensor: {"message": f"No data found for {target_sensor}."}
            }
            continue

        sensor_info = sensor_types.get(target_sensor, {})
        timeseries_data = sensor_info.get("timeseries_data", [])

        try:
            df = pd.DataFrame(timeseries_data)
            if "datetime" in df.columns:
                df.rename(columns={"datetime": "timestamp"}, inplace=True)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception as e:
            logging.error(f"Data error for sensor {sensor_id}: {e}")
            response[sensor_id] = {target_sensor: {"error": "Data format issue."}}
            continue

        if df.empty:
            response[sensor_id] = {target_sensor: {"message": "No data available."}}
            continue

        norm = float(df["reading_value"].mean())
        latest_value = float(df.sort_values(by="timestamp").iloc[-1]["reading_value"])

        if latest_value > norm:
            trend = "rising"
        elif latest_value < norm:
            trend = "falling"
        else:
            trend = "stable"

        response[sensor_id] = {
            target_sensor: {
                "norm": round(norm, 2),
                "latest_reading": round(latest_value, 2),
                "trend": trend,
                "message": f"{target_sensor} trend is {trend} compared to average.",
            }
        }

    if not response:
        return {"message": f"No trend analysis found for {target_sensor}."}

    return response


def analyze_hvac_anomalies(sensor_data):
    """
    Analyzes HVAC sensor data to detect anomalies in the past week.

    Expected input: either a Python dictionary or a JSON string in the following nested format:

    {
      "1": {
          "HVAC_1": {
             "timeseries_data": [
                {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99, "sensor_id": "HVAC_1"},
                {"datetime": "2025-02-10 05:32:11", "reading_value": 27.99, "sensor_id": "HVAC_1"},
                ...
             ]
          },
          "Other_Sensor": { ... }
      },
      "2": {
          "HVAC_2": {
             "timeseries_data": [
                {"datetime": "2025-02-10 05:35:00", "reading_value": 28.05, "sensor_id": "HVAC_2"},
                {"datetime": "2025-02-10 05:35:12", "reading_value": 28.07, "sensor_id": "HVAC_2"},
                ...
             ]
          }
      }
    }

    For each sensor type (only those whose sensor type name contains "HVAC", case-insensitive):
      - Converts the list of readings from "timeseries_data" into a DataFrame.
      - Renames "datetime" to "timestamp" (if present) and converts it to datetime objects.
      - Filters the readings to only include data from the past 7 days.
      - Calculates the 25th percentile (Q1), 75th percentile (Q3), and IQR.
      - Identifies outliers where reading_value is below (Q1 - 1.5*IQR) or above (Q3 + 1.5*IQR).

    Returns:
      A dictionary with each HVAC sensor's identifier (taken from the sensor type key) as a key and a summary of the anomaly analysis as its value.
      For example:

      {
          "HVAC_1": {
              "anomaly_count": 3,
              "message": "Sensor HVAC_1 detected 3 anomalies in the past week."
          },
          "HVAC_2": {
              "message": "No significant anomalies detected in the HVAC system."
          }
      }
    """
    # Parse JSON if necessary.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # If sensor_data is provided as a list (data for one sensor), wrap it in a dict.
    if isinstance(sensor_data, list):
        sensor_data = {"1": sensor_data}

    response = {}
    now = pd.Timestamp.now()

    # Iterate over each outer sensor key.
    for outer_key, sensor_types in sensor_data.items():
        # Iterate over each sensor type within the outer key.
        for sensor_type, sensor_info in sensor_types.items():
            # Process only sensor types whose name contains "HVAC" (case-insensitive).
            if "HVAC" not in sensor_type.upper():
                continue

            timeseries_data = sensor_info.get("timeseries_data", [])
            try:
                df = pd.DataFrame(timeseries_data)
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            except Exception as e:
                logging.error(f"Data conversion error for sensor {sensor_type}: {e}")
                response[sensor_type] = {"error": "Invalid sensor data format"}
                continue

            # Filter data for the past 7 days.
            df = df[df["timestamp"] >= now - pd.Timedelta(days=7)]
            if df.empty:
                response[sensor_type] = {
                    "message": "No HVAC data available for the past week."
                }
                continue

            # Compute quartiles and IQR.
            Q1 = df["reading_value"].quantile(0.25)
            Q3 = df["reading_value"].quantile(0.75)
            IQR = Q3 - Q1

            # Identify outliers.
            outliers = df[
                (df["reading_value"] < Q1 - 1.5 * IQR)
                | (df["reading_value"] > Q3 + 1.5 * IQR)
            ]

            if not outliers.empty:
                response[sensor_type] = {
                    "anomaly_count": int(len(outliers)),
                    "message": f"Sensor {sensor_type} detected {len(outliers)} anomalies in the past week.",
                }
            else:
                response[sensor_type] = {
                    "message": "No significant anomalies detected in the HVAC system."
                }

    if not response:
        return {"message": "No HVAC sensor data available."}

    return response


def analyze_supply_return_temp_difference(sensor_data):
    """
    Compares supply and return air temperature sensor data from a single nested JSON structure
    and calculates the average difference.

    Expected input (as a dict or JSON string):
      {
          "1": {
              "Supply_Air_Temperature_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 28.5},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 29.0},
                      {"datetime": "2025-02-10 05:33:00", "reading_value": 28.0}
                  ]
              },
              "Return_Air_Temperature_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 27.0},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 26.5},
                      {"datetime": "2025-02-10 05:33:00", "reading_value": 27.0}
                  ]
              }
          },
          "2": {
              "Supply_Air_Temperature_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:34:00", "reading_value": 23.5},
                      {"datetime": "2025-02-10 05:35:00", "reading_value": 22.5},
                      {"datetime": "2025-02-10 05:36:00", "reading_value": 21.5}
                  ]
              },
              "Return_Air_Temperature_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:34:00", "reading_value": 27.5},
                      {"datetime": "2025-02-10 05:35:00", "reading_value": 27.0},
                      {"datetime": "2025-02-10 05:36:00", "reading_value": 27.0}
                  ]
              }
          }
      }

    The function aggregates readings for "Supply_Air_Temperature_Sensor" and "Return_Air_Temperature_Sensor"
    across all sensor IDs, calculates the average reading for each, computes their difference, and returns a summary.

    Returns:
      A dictionary with:
        - average_supply_temperature: Average supply temperature.
        - average_return_temperature: Average return temperature.
        - temperature_difference: Difference (supply minus return).
        - message: A descriptive message.
    """
    # Parse sensor_data if it is a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Initialize lists to collect readings.
    supply_readings = []
    return_readings = []

    # Iterate over each sensor ID and aggregate readings.
    for sensor_id, sensor_types in sensor_data.items():
        if "Supply_Air_Temperature_Sensor" in sensor_types:
            supply_readings.extend(
                sensor_types["Supply_Air_Temperature_Sensor"].get("timeseries_data", [])
            )
        if "Return_Air_Temperature_Sensor" in sensor_types:
            return_readings.extend(
                sensor_types["Return_Air_Temperature_Sensor"].get("timeseries_data", [])
            )

    if not supply_readings:
        return {"error": "No supply air temperature data found"}
    if not return_readings:
        return {"error": "No return air temperature data found"}

    try:
        # Process supply data.
        df_supply = pd.DataFrame(supply_readings)
        if "datetime" in df_supply.columns:
            df_supply = df_supply.rename(columns={"datetime": "timestamp"})
        df_supply["timestamp"] = pd.to_datetime(df_supply["timestamp"])
        df_supply = df_supply.sort_values(by="timestamp")
        avg_supply = df_supply["reading_value"].mean()

        # Process return data.
        df_return = pd.DataFrame(return_readings)
        if "datetime" in df_return.columns:
            df_return = df_return.rename(columns={"datetime": "timestamp"})
        df_return["timestamp"] = pd.to_datetime(df_return["timestamp"])
        df_return = df_return.sort_values(by="timestamp")
        avg_return = df_return["reading_value"].mean()

    except Exception as e:
        logging.error(f"Error processing temperature data: {e}")
        return {"error": "Data conversion error"}

    diff = avg_supply - avg_return
    result = {
        "average_supply_temperature": round(avg_supply, 2),
        "average_return_temperature": round(avg_return, 2),
        "temperature_difference": round(diff, 2),
        "message": (
            f"Average supply temperature is {avg_supply:.2f}°C, "
            f"average return temperature is {avg_return:.2f}°C, with a difference of {diff:.2f}°C."
        ),
    }
    return result


def analyze_air_flow_variation(sensor_data, target_sensor="Air_Flow_Sensor"):
    """
    Analyzes airflow variation for the specified target sensor from a nested JSON structure.

    Parameters:
      - sensor_data: JSON string or dict with structure:
        {
            "1": {
                "Air_Flow_Sensor": {
                    "timeseries_data": [
                        {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                        ...
                    ]
                }
            },
            "2": { ... }
        }

      - target_sensor: default "Air_Flow_Sensor", can be customized if needed.

    For each timeseries ID:
      - Extracts data for target_sensor.
      - Computes mean, std deviation, coefficient of variation.
      - Reports stability/instability based on CV.

    Returns:
      A nested dict mapping each timeseries ID to results for the target_sensor.
    """
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid JSON input"}

    response = {}

    for sensor_id, sensor_types in sensor_data.items():
        if target_sensor not in sensor_types:
            response[sensor_id] = {
                target_sensor: {"message": f"No data available for {target_sensor}."}
            }
            continue

        timeseries_data = sensor_types[target_sensor].get("timeseries_data", [])
        if not timeseries_data:
            response[sensor_id] = {
                target_sensor: {"message": f"No readings found for {target_sensor}."}
            }
            continue

        try:
            df = pd.DataFrame(timeseries_data)
            if "datetime" in df.columns:
                df.rename(columns={"datetime": "timestamp"}, inplace=True)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception as e:
            logging.error(f"Data conversion error for sensor {sensor_id}: {e}")
            response[sensor_id] = {target_sensor: {"error": "Data formatting error"}}
            continue

        mean_val = df["reading_value"].mean()
        std_val = df["reading_value"].std() or 0.0
        cv = std_val / mean_val if mean_val else 0

        response[sensor_id] = {
            target_sensor: {
                "mean_airflow": round(mean_val, 2),
                "std_dev_airflow": round(std_val, 2),
                "coefficient_of_variation": round(cv, 2),
                "message": (
                    f"{target_sensor} coefficient of variation: {cv:.2f}. "
                    + ("Stable airflow." if cv < 0.1 else "High variation detected.")
                ),
            }
        }

    return response


def analyze_pressure_trend(sensor_data, expected_range=(0.5, 1.5)):
    """
    Analyzes static pressure sensor data to check if average readings are within an expected range,
    accepting a nested JSON structure.

    Expected input (as a Python dict or JSON string):
      {
          "1": {
              "Static_Pressure_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 1.2},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 1.3},
                      ...
                  ]
              }
          },
          "2": {
              "Static_Pressure_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:35:00", "reading_value": 0.8},
                      {"datetime": "2025-02-10 05:35:12", "reading_value": 0.7},
                      ...
                  ]
              }
          }
      }

    For each sensor type:
      - Converts the list of readings (from "timeseries_data") into a DataFrame.
      - Renames "datetime" to "timestamp" (if necessary) and converts it to datetime objects.
      - Computes the average static pressure.
      - Compares it with the expected_range.

    Returns:
      A nested dictionary where each sensor ID maps to sensor type keys with their analysis.
    """
    # Parse JSON string if necessary.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # If sensor_data is a list (data for one sensor), wrap it in a dictionary.
    if isinstance(sensor_data, list):
        sensor_data = {"1": sensor_data}

    response = {}
    for sensor_id, sensor_types in sensor_data.items():
        response[sensor_id] = {}
        for sensor_type, sensor_info in sensor_types.items():
            # Get the readings from the "timeseries_data" key.
            timeseries_data = sensor_info.get("timeseries_data", [])
            try:
                df = pd.DataFrame(timeseries_data)
                # Rename "datetime" to "timestamp" if present.
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            except Exception as e:
                logging.error(
                    f"Data processing error for sensor {sensor_id}, type {sensor_type}: {e}"
                )
                response[sensor_id][sensor_type] = {
                    "error": "Invalid sensor data format"
                }
                continue

            if df.empty:
                response[sensor_id][sensor_type] = {
                    "message": "No data available for this sensor."
                }
                continue

            avg_pressure = df["reading_value"].mean()

            if expected_range[0] <= avg_pressure <= expected_range[1]:
                message = (
                    f"Sensor {sensor_id} ({sensor_type}) average pressure "
                    f"{avg_pressure:.2f} is within the expected range."
                )
                status = "normal"
            else:
                message = (
                    f"Sensor {sensor_id} ({sensor_type}) average pressure "
                    f"{avg_pressure:.2f} is out of the expected range {expected_range}."
                )
                status = "abnormal"

            response[sensor_id][sensor_type] = {
                "average_pressure": round(avg_pressure, 2),
                "status": status,
                "message": message,
            }

    if not response:
        return {"message": "No pressure sensor data found."}

    return response


def analyze_sensor_trend(sensor_data, window=3):
    """
    Analyzes the trend of sensor readings using a moving average from a nested JSON structure.

    Expected input (as a Python dict or JSON string):
      {
          "1": {
              "Sensor_Type_A": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 27.99},
                      ...
                  ]
              },
              "Sensor_Type_B": { ... }
          },
          "2": {
              "Sensor_Type_A": { ... }
          }
      }

    For each sensor type:
      - Converts the list of readings (from "timeseries_data") into a DataFrame.
      - Renames "datetime" to "timestamp" (if necessary) and converts it to datetime objects.
      - Sorts by timestamp and computes a rolling average with the specified window.
      - Determines the trend as "upward", "downward", or "stable" by comparing the first and last rolling mean.

    Returns:
      A nested dictionary where each sensor ID maps to sensor type keys with their trend analysis details.
    """
    # Parse JSON string if necessary.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # If sensor_data is provided as a list, wrap it in a dict with a default key "1".
    if isinstance(sensor_data, list):
        sensor_data = {"1": sensor_data}

    response = {}
    trend_threshold = 0.05  # threshold to decide if change is significant (adjustable)

    # Process each sensor ID.
    for sensor_id, sensor_types in sensor_data.items():
        response[sensor_id] = {}
        # Process each sensor type for the current sensor ID.
        for sensor_type, sensor_info in sensor_types.items():
            timeseries_data = sensor_info.get("timeseries_data", [])
            try:
                # Convert list of readings into a DataFrame.
                df = pd.DataFrame(timeseries_data)
                # Rename "datetime" to "timestamp" if needed.
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp")
                # Compute rolling average.
                df["rolling_mean"] = (
                    df["reading_value"].rolling(window=window, min_periods=1).mean()
                )
            except Exception as e:
                logging.error(
                    f"Data conversion error for sensor {sensor_id}, type {sensor_type}: {e}"
                )
                response[sensor_id][sensor_type] = {
                    "error": "Invalid sensor data format"
                }
                continue

            # Compute trend using difference between the first and last rolling average values.
            trend_diff = df["rolling_mean"].iloc[-1] - df["rolling_mean"].iloc[0]
            if abs(trend_diff) < trend_threshold:
                trend = "stable"
            elif trend_diff > 0:
                trend = "upward"
            else:
                trend = "downward"

            response[sensor_id][sensor_type] = {
                "initial_rolling_mean": df["rolling_mean"].iloc[0],
                "latest_rolling_mean": df["rolling_mean"].iloc[-1],
                "trend": trend,
                "difference": trend_diff,
            }

    return response


def aggregate_sensor_data(sensor_data, freq="H"):
    """
    Aggregates sensor data into defined time intervals (e.g., hourly, daily) and computes summary statistics,
    accepting a nested JSON structure.

    Expected input (as a Python dict or JSON string):
      {
          "1": {
              "Sensor_Type_A": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 27.99},
                      ...
                  ]
              },
              "Sensor_Type_B": { ... }
          },
          "2": {
              "Sensor_Type_A": { ... }
          }
      }

    Returns:
      A nested dictionary mapping sensor IDs to sensor type keys and their aggregated summaries.
      Each summary (list of records) includes the mean, standard deviation, minimum, and maximum values,
      with timestamps converted to string format.
    """
    # Parse JSON string if needed.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    aggregated_results = {}

    # Iterate over each sensor ID.
    for sensor_id, sensor_types in sensor_data.items():
        aggregated_results[sensor_id] = {}
        # Iterate over each sensor type within this sensor ID.
        for sensor_type, sensor_info in sensor_types.items():
            timeseries_data = sensor_info.get("timeseries_data", [])
            try:
                df = pd.DataFrame(timeseries_data)
                # Rename "datetime" column to "timestamp" if necessary.
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp")
                df.set_index("timestamp", inplace=True)
                # Resample and compute summary statistics.
                agg_df = (
                    df["reading_value"]
                    .resample(freq)
                    .agg(["mean", "std", "min", "max"])
                )
                # Reset index and convert timestamp to string.
                agg_df = agg_df.reset_index()
                agg_df["timestamp"] = agg_df["timestamp"].dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                aggregated_results[sensor_id][sensor_type] = agg_df.to_dict(
                    orient="records"
                )
            except Exception as e:
                logging.error(
                    f"Aggregation error for sensor {sensor_id}, type {sensor_type}: {e}"
                )
                aggregated_results[sensor_id][sensor_type] = {
                    "error": "Aggregation failed"
                }

    return aggregated_results


def correlate_sensors(sensor_data_dict):
    """
    Computes the correlation matrix among multiple timeseries from a JSON structure.

    Expected input (as a Python dict or JSON string):
      {
          "249a4c9c-fe31-4649-a119-452e5e8e7dc5": [
              {"datetime": "2025-03-15 00:02:01", "reading_value": 10},
              {"datetime": "2025-03-15 00:03:01", "reading_value": 11},
              ...
          ],
          "95ae1ca6-1806-40b9-9493-9b6be51a5e03": [
              {"datetime": "2025-03-15 00:02:01", "reading_value": 12},
              {"datetime": "2025-03-15 00:03:01", "reading_value": 13},
              ...
          ]
      }

    The function processes each timeseries ID as a unique sensor, merges data on timestamps
    (with a tolerance of 1 minute), and computes the Pearson correlation between readings.

    Returns:
      A correlation matrix as a nested dictionary, or an error dictionary if processing fails.
    """
    # Parse JSON string to dict if needed
    if isinstance(sensor_data_dict, str):
        try:
            sensor_data_dict = json.loads(sensor_data_dict)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    dfs = []

    # Process each timeseries ID
    for timeseries_id, timeseries_data in sensor_data_dict.items():
        try:
            # Convert timeseries data to DataFrame
            df = pd.DataFrame(timeseries_data)
            if "datetime" not in df.columns or "reading_value" not in df.columns:
                logging.error(f"Missing required columns in timeseries {timeseries_id}")
                continue

            # Rename datetime to timestamp and convert to datetime
            df = df.rename(columns={"datetime": "timestamp"})
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp")

            # Rename reading_value column to the timeseries ID
            df = df[["timestamp", "reading_value"]].rename(
                columns={"reading_value": timeseries_id}
            )
            dfs.append(df)
        except Exception as e:
            logging.error(f"Error processing timeseries {timeseries_id}: {e}")
            continue

    if not dfs:
        return {"error": "No valid timeseries data to correlate."}

    # Merge all DataFrames on the timestamp column using asof merge with a tolerance of 1 minute
    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge_asof(
            merged_df,
            df,
            on="timestamp",
            tolerance=pd.Timedelta("1min"),
            direction="nearest",
        )

    # Drop the timestamp column and compute the correlation matrix
    corr_matrix = merged_df.drop(columns=["timestamp"]).corr(method="pearson")
    return corr_matrix.to_dict()


def compute_air_quality_index(sensor_data):
    """
    Computes a composite Air Quality Index (AQI) based on selected pollutant sensors from a nested JSON structure.

    Expected sensor keys (if available) in the nested input:
      - "PM2.5_Level_Sensor_Standard"
      - "PM10_Level_Sensor_Standard"
      - "NO2_Level_Sensor"
      - "CO_Level_Sensor"
      - "CO2_Level_Sensor"

    Input format (as a Python dict or JSON string):
      {
          "1": {
              "PM2.5_Level_Sensor_Standard": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                      ...
                  ]
              },
              "Other_Sensor": { ... }
          },
          "2": {
              "PM10_Level_Sensor_Standard": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:35:00", "reading_value": 45.0},
                      ...
                  ]
              },
              "NO2_Level_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:35:12", "reading_value": 38.0},
                      ...
                  ]
              }
          },
          ...
      }

    For each expected sensor, the function:
      - Aggregates all readings across the nested structure.
      - Converts the data to a DataFrame, renames the "datetime" column (if present) to "timestamp" and converts it.
      - Sorts by timestamp and takes the latest reading.
      - Normalizes the reading by dividing by an arbitrary threshold.
      - Multiplies by a weight to obtain a component value.

    Finally, it sums the weighted components to compute the composite AQI and assigns a health status.
    """
    # Parse JSON string if needed.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Define arbitrary thresholds and weights.
    thresholds = {
        "PM2.5_Level_Sensor_Standard": 35,
        "PM10_Level_Sensor_Standard": 50,
        "NO2_Level_Sensor": 40,
        "CO_Level_Sensor": 9,
        "CO2_Level_Sensor": 1000,
    }

    weights = {
        "PM2.5_Level_Sensor_Standard": 0.3,
        "PM10_Level_Sensor_Standard": 0.2,
        "NO2_Level_Sensor": 0.2,
        "CO_Level_Sensor": 0.15,
        "CO2_Level_Sensor": 0.15,
    }

    index_components = {}

    # For each expected sensor type, gather all readings from the nested structure.
    for sensor_type, threshold in thresholds.items():
        aggregated_readings = []
        # Loop over each outer key (sensor ID) in the nested structure.
        for sensor_id, sensor_types in sensor_data.items():
            if sensor_type in sensor_types:
                timeseries = sensor_types[sensor_type].get("timeseries_data", [])
                aggregated_readings.extend(timeseries)
        if not aggregated_readings:
            continue
        try:
            df = pd.DataFrame(aggregated_readings)
            if "datetime" in df.columns:
                df = df.rename(columns={"datetime": "timestamp"})
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp")
            latest_value = df.iloc[-1]["reading_value"]
            # Normalize the latest reading (simple ratio normalization).
            normalized = latest_value / threshold
            index_components[sensor_type] = normalized * weights[sensor_type]
        except Exception as e:
            logging.error(
                f"Error computing AQI component for sensor {sensor_type}: {e}"
            )

    if not index_components:
        return {"error": "Insufficient data for AQI calculation."}

    aqi = sum(index_components.values())

    # Define a simple category (arbitrary ranges for demonstration purposes)
    if aqi < 0.5:
        status = "Good"
    elif aqi < 1:
        status = "Moderate"
    elif aqi < 1.5:
        status = "Unhealthy for Sensitive Groups"
    else:
        status = "Unhealthy"

    return {"AQI": aqi, "Status": status, "Components": index_components}


def generate_health_alerts(sensor_data, thresholds):
    """
    Generates alerts if the latest sensor readings exceed specified threshold ranges,
    accepting a nested JSON structure.

    Parameters:
      - sensor_data: A dict or JSON string in the following format:
          {
              "1": {
                  "PM2.5_Level_Sensor_Standard": {
                      "timeseries_data": [
                          {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                          {"datetime": "2025-02-10 05:32:11", "reading_value": 27.99},
                          ...
                      ]
                  },
                  "Other_Sensor": { ... }
              },
              "2": {
                  "NO2_Level_Sensor": {
                      "timeseries_data": [
                          {"datetime": "2025-02-10 05:35:00", "reading_value": 38.0},
                          {"datetime": "2025-02-10 05:35:12", "reading_value": 39.5},
                          ...
                      ]
                  }
              }
          }
      - thresholds: A dict mapping sensor names (as used in the inner keys) to a tuple (min_value, max_value).

    For each sensor type specified in thresholds, the function finds the latest reading and returns an alert
    if the reading is below min_value or above max_value. The resulting alerts are keyed by a unique identifier
    in the format "sensorID_sensorType".

    Returns a dictionary with alert messages per sensor.
    """
    # Convert sensor_data from JSON string to dict if needed.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    alerts = {}

    # Iterate over each outer sensor ID.
    for sensor_id, sensor_types in sensor_data.items():
        # Iterate over each sensor type within this sensor ID.
        for sensor_type, sensor_info in sensor_types.items():
            # Process only if sensor_type is among those in thresholds.
            if sensor_type not in thresholds:
                continue

            min_val, max_val = thresholds[sensor_type]
            readings = sensor_info.get("timeseries_data", [])
            unique_key = f"{sensor_id}_{sensor_type}"

            if not readings:
                alerts[unique_key] = "No data available."
                continue

            try:
                df = pd.DataFrame(readings)
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp")
                latest_value = df.iloc[-1]["reading_value"]
            except Exception as e:
                logging.error(
                    f"Error processing sensor {sensor_id} ({sensor_type}): {e}"
                )
                alerts[unique_key] = "Data error."
                continue

            if latest_value < min_val or latest_value > max_val:
                alerts[unique_key] = (
                    f"Alert: Latest reading {latest_value} out of range [{min_val}, {max_val}]."
                )
            else:
                alerts[unique_key] = (
                    f"OK: Latest reading {latest_value} within acceptable range."
                )

    return alerts


def detect_anomalies(sensor_data, method="zscore", threshold=3, robust=False):
    """
    Detects anomalies in sensor data using a statistical approach from a nested JSON structure.

    Parameters:
      - sensor_data: A dict or JSON string of sensor data. Expected format:
            {
                "1": {
                    "Sensor_Type_A": {
                        "timeseries_data": [
                            {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                            {"datetime": "2025-02-10 05:32:11", "reading_value": 27.99},
                            ...
                        ]
                    },
                    "Sensor_Type_B": { ... }
                },
                "2": { ... }
            }
      - method: Currently supports only "zscore" (standard or robust based on the `robust` flag).
      - threshold: The z-score threshold above which a reading is flagged as an anomaly.
      - robust: If True, uses the median and median absolute deviation (MAD) for z-score calculation,
                which is more robust to outliers.

    Returns:
      A dictionary mapping flattened sensor names (e.g. "1_Sensor_Type_A") to a list of anomalous readings.
      Each anomalous reading includes the timestamp, reading_value, and computed zscore.
    """
    # Convert JSON string to dict if needed.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    anomalies = {}

    # Iterate over each sensor ID in the nested structure.
    for sensor_id, sensor_types in sensor_data.items():
        # Iterate over each sensor type.
        for sensor_type, sensor_info in sensor_types.items():
            unique_key = f"{sensor_id}_{sensor_type}"
            timeseries_data = sensor_info.get("timeseries_data", [])
            try:
                df = pd.DataFrame(timeseries_data)
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp")

                if robust:
                    median_val = df["reading_value"].median()
                    mad = np.median(np.abs(df["reading_value"] - median_val))
                    if mad == 0:
                        mad = 1  # Avoid division by zero
                    df["zscore"] = 0.6745 * (df["reading_value"] - median_val) / mad
                else:
                    mean_val = df["reading_value"].mean()
                    std_val = df["reading_value"].std() or 1  # Avoid division by zero
                    df["zscore"] = (df["reading_value"] - mean_val) / std_val

                # Flag anomalies where the absolute z-score exceeds the threshold.
                anomaly_df = df[np.abs(df["zscore"]) > threshold].copy()
                anomaly_df = anomaly_df.assign(
                    timestamp=anomaly_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                )
                anomalies[unique_key] = anomaly_df[
                    ["timestamp", "reading_value", "zscore"]
                ].to_dict(orient="records")
            except Exception as e:
                logging.error(f"Error detecting anomalies for sensor {unique_key}: {e}")
                anomalies[unique_key] = {
                    "error": "Anomaly detection failed",
                    "details": str(e),
                }

    return anomalies


def analyze_noise_levels(
    sensor_data, sensor_key="Sound_Noise_Sensor_MEMS", threshold=90
):
    """
    Analyzes noise level data from a nested JSON structure.

    Aggregates readings for the specified sensor_key from across all sensor IDs.
    Computes the mean, min, max, standard deviation and flags if the latest reading exceeds the threshold.

    Parameters:
      - sensor_data: A dict or JSON string in the following format:
            {
                "1": {
                    "Sound_Noise_Sensor_MEMS": {
                        "timeseries_data": [
                            {"datetime": "2025-02-10 05:31:59", "reading_value": 87.5},
                            {"datetime": "2025-02-10 05:32:11", "reading_value": 92.0},
                            ...
                        ]
                    },
                    "Other_Sensor": { ... }
                },
                "2": {
                    "Sound_Noise_Sensor_MEMS": {
                        "timeseries_data": [
                            {"datetime": "2025-02-10 05:35:00", "reading_value": 89.0},
                            {"datetime": "2025-02-10 05:35:12", "reading_value": 91.5},
                            ...
                        ]
                    }
                }
            }
      - sensor_key: The sensor type key to look for (default: "Sound_Noise_Sensor_MEMS").
      - threshold: The noise level threshold (default: 90).

    Returns:
      A dictionary with summary statistics and an alert message.
    """
    # Parse sensor_data from JSON string if needed.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Aggregate readings for the specified sensor_key across all sensor IDs.
    aggregated_readings = []
    for sensor_id, sensor_types in sensor_data.items():
        if sensor_key in sensor_types:
            readings = sensor_types[sensor_key].get("timeseries_data", [])
            aggregated_readings.extend(readings)

    if not aggregated_readings:
        return {"error": f"No data found for {sensor_key}"}

    try:
        df = pd.DataFrame(aggregated_readings)
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")
        latest = df.iloc[-1]["reading_value"]
        summary = {
            "mean": float(df["reading_value"].mean()),
            "min": float(df["reading_value"].min()),
            "max": float(df["reading_value"].max()),
            "std": float(df["reading_value"].std()),
            "latest": float(latest),
        }
        summary["alert"] = (
            "High noise level" if latest > threshold else "Normal noise level"
        )
        return summary
    except Exception as e:
        logging.error(f"Error analyzing noise levels: {e}")
        return {"error": "Failed to analyze noise levels"}


def analyze_air_quality(
    sensor_data, sensor_key="Air_Quality_Sensor", thresholds=(50, 100)
):
    """
    Analyzes air quality sensor data from a nested JSON structure.

    Aggregates readings for the specified sensor_key across sensor IDs.
    Computes the average air quality index and classifies it based on thresholds.

    Expected input (as a Python dict or JSON string):
      {
         "1": {
             "Air_Quality_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:31:59", "reading_value": 45},
                     {"datetime": "2025-02-10 05:32:11", "reading_value": 50},
                     ...
                 ]
             },
             "Other_Sensor": { ... }
         },
         "2": {
             "Air_Quality_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:35:00", "reading_value": 55},
                     {"datetime": "2025-02-10 05:35:12", "reading_value": 60},
                     ...
                 ]
             }
         }
      }

    Returns a dictionary containing:
        - average_air_quality: computed average reading_value.
        - status: classification ("Good", "Moderate", or "Poor").
        - min: minimum reading_value.
        - max: maximum reading_value.
    """
    # Parse sensor_data if it's a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Aggregate readings for the specified sensor_key across sensor IDs.
    aggregated_readings = []
    for sensor_id, sensor_types in sensor_data.items():
        if sensor_key in sensor_types:
            readings = sensor_types[sensor_key].get("timeseries_data", [])
            aggregated_readings.extend(readings)

    if not aggregated_readings:
        return {"error": f"No data found for {sensor_key}"}

    try:
        df = pd.DataFrame(aggregated_readings)
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")
        avg_quality = float(df["reading_value"].mean())
        if avg_quality <= thresholds[0]:
            status = "Good"
        elif avg_quality <= thresholds[1]:
            status = "Moderate"
        else:
            status = "Poor"
        return {
            "average_air_quality": avg_quality,
            "status": status,
            "min": float(df["reading_value"].min()),
            "max": float(df["reading_value"].max()),
        }
    except Exception as e:
        logging.error(f"Error analyzing air quality: {e}")
        return {"error": "Failed to analyze air quality"}


def analyze_formaldehyde_levels(
    sensor_data, sensor_key="Formaldehyde_Level_Sensor", threshold=0.1
):
    """
    Analyzes formaldehyde sensor readings from a nested JSON structure.

    Aggregates readings for the specified sensor_key across sensor IDs.
    Computes summary statistics and flags if the latest reading exceeds the threshold.

    Expected input (as a Python dict or JSON string):
      {
         "1": {
             "Formaldehyde_Level_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:31:59", "reading_value": 0.08},
                     {"datetime": "2025-02-10 05:32:11", "reading_value": 0.09},
                     ...
                 ]
             },
             "Other_Sensor": { ... }
         },
         "2": {
             "Formaldehyde_Level_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:35:00", "reading_value": 0.11},
                     {"datetime": "2025-02-10 05:35:12", "reading_value": 0.10},
                     ...
                 ]
             }
         }
      }

    Returns a dictionary containing:
      - mean, min, max, std, and latest reading_value.
      - an alert message if the latest reading exceeds the threshold.
    """
    # Parse sensor_data if it is a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Aggregate readings for the specified sensor_key across all sensor IDs.
    aggregated_readings = []
    for sensor_id, sensor_types in sensor_data.items():
        if sensor_key in sensor_types:
            readings = sensor_types[sensor_key].get("timeseries_data", [])
            aggregated_readings.extend(readings)

    if not aggregated_readings:
        return {"error": f"No data found for {sensor_key}"}

    try:
        df = pd.DataFrame(aggregated_readings)
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")
        latest = float(df.iloc[-1]["reading_value"])
        summary = {
            "mean": float(df["reading_value"].mean()),
            "min": float(df["reading_value"].min()),
            "max": float(df["reading_value"].max()),
            "std": float(df["reading_value"].std()),
            "latest": latest,
        }
        summary["alert"] = (
            "High formaldehyde level"
            if latest > threshold
            else "Normal formaldehyde level"
        )
        return summary
    except Exception as e:
        logging.error(f"Error analyzing formaldehyde levels: {e}")
        return {"error": "Failed to analyze formaldehyde levels"}


def analyze_co2_levels(sensor_data, sensor_key="CO2_Level_Sensor", threshold=1000):
    """
    Analyzes CO2 sensor readings from a nested JSON structure.

    Aggregates readings for the specified sensor_key across sensor IDs,
    computes summary statistics, and flags if the latest reading exceeds the threshold.

    Expected input (as a Python dict or JSON string):
      {
          "1": {
              "CO2_Level_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:31:59", "reading_value": 950},
                      {"datetime": "2025-02-10 05:32:11", "reading_value": 980},
                      ...
                  ]
              },
              "Other_Sensor": { ... }
          },
          "2": {
              "CO2_Level_Sensor": {
                  "timeseries_data": [
                      {"datetime": "2025-02-10 05:35:00", "reading_value": 1020},
                      {"datetime": "2025-02-10 05:35:12", "reading_value": 1005},
                      ...
                  ]
              }
          }
      }

    Returns a dictionary with:
      - mean, min, max, std, and latest reading_value.
      - an alert message if the latest reading exceeds the threshold.
    """
    # Parse sensor_data if provided as a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Aggregate readings for the specified sensor_key across sensor IDs.
    aggregated_readings = []
    for sensor_id, sensor_types in sensor_data.items():
        if sensor_key in sensor_types:
            readings = sensor_types[sensor_key].get("timeseries_data", [])
            aggregated_readings.extend(readings)

    if not aggregated_readings:
        return {"error": f"No data found for {sensor_key}"}

    try:
        df = pd.DataFrame(aggregated_readings)
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")
        latest = float(df.iloc[-1]["reading_value"])
        summary = {
            "mean": float(df["reading_value"].mean()),
            "min": float(df["reading_value"].min()),
            "max": float(df["reading_value"].max()),
            "std": float(df["reading_value"].std()),
            "latest": latest,
        }
        summary["alert"] = (
            "High CO2 level" if latest > threshold else "Normal CO2 level"
        )
        return summary
    except Exception as e:
        logging.error(f"Error analyzing CO2 levels: {e}")
        return {"error": "Failed to analyze CO2 levels"}


def analyze_pm_levels(
    sensor_data,
    sensor_keys=[
        "PM1_Level_Sensor_Standard",
        "PM2_5_Level_Sensor_Standard",
        "PM10_Level_Sensor_Standard",
    ],
    thresholds={
        "PM1_Level_Sensor_Standard": 50,
        "PM2_5_Level_Sensor_Standard": 30,
        "PM10_Level_Sensor_Standard": 50,
    },
):
    """
    Analyzes particulate matter (PM) sensor data from a nested JSON structure.

    Expected input (as a Python dict or JSON string):
      {
          "1": {
              "PM1_Level_Sensor_Standard": {
                  "timeseries_data": [ ... ]
              },
              "PM2.5_Level_Sensor_Standard": {
                  "timeseries_data": [ ... ]
              },
              "PM10_Level_Sensor_Standard": {
                  "timeseries_data": [ ... ]
              },
              "Other_Sensor": { ... }
          },
          "2": {
              "PM1_Level_Sensor_Standard": { "timeseries_data": [ ... ] },
              "PM2.5_Level_Sensor_Standard": { "timeseries_data": [ ... ] },
              "PM10_Level_Sensor_Standard": { "timeseries_data": [ ... ] }
          }
      }

    For each sensor key, the function aggregates readings across sensor IDs,
    computes summary statistics (mean, min, max, std, latest value) and flags if
    the latest reading exceeds its defined threshold.

    Returns a dictionary mapping each sensor key to its analysis summary.
    """
    # Parse sensor_data if it's a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor data"}

    # If sensor_data is a list (data for a single sensor), wrap it in a dict.
    if isinstance(sensor_data, list):
        sensor_data = {"1": sensor_data}

    analysis = {}
    for key in sensor_keys:
        # Aggregate readings for this key across all sensor IDs.
        aggregated_readings = []
        for sensor_id, sensor_types in sensor_data.items():
            if key in sensor_types:
                readings = sensor_types[key].get("timeseries_data", [])
                aggregated_readings.extend(readings)
        if not aggregated_readings:
            analysis[key] = {"error": "No data available"}
            continue
        try:
            df = pd.DataFrame(aggregated_readings)
            if "datetime" in df.columns:
                df = df.rename(columns={"datetime": "timestamp"})
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp")
            latest = float(df.iloc[-1]["reading_value"])
            summary = {
                "mean": float(df["reading_value"].mean()),
                "min": float(df["reading_value"].min()),
                "max": float(df["reading_value"].max()),
                "std": float(df["reading_value"].std()),
                "latest": latest,
            }
            thres = thresholds.get(key, None)
            if thres is not None:
                summary["alert"] = (
                    f"High {key} reading" if latest > thres else f"Normal {key} reading"
                )
            else:
                summary["alert"] = "Threshold not defined"
            analysis[key] = summary
        except Exception as e:
            logging.error(f"Error analyzing {key}: {e}")
            analysis[key] = {"error": f"Failed to analyze {key}"}
    return analysis


def analyze_temperatures(
    sensor_data, sensor_key="Air_Temperature_Sensor", acceptable_range=(18, 27)
):
    """
    Analyzes temperature sensor data from a nested JSON structure.

    Aggregates readings for the specified sensor_key across sensor IDs.
    Computes summary statistics (mean, min, max, std, and latest reading) and flags if the latest
    reading is outside the acceptable range.

    Expected input (as a Python dict or JSON string):
      {
         "1": {
             "Air_Temperature_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:31:59", "reading_value": 22.5},
                     {"datetime": "2025-02-10 05:32:11", "reading_value": 23.0},
                     ...
                 ]
             },
             "Other_Sensor": { ... }
         },
         "2": {
             "Air_Temperature_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:33:00", "reading_value": 24.0},
                     {"datetime": "2025-02-10 05:33:15", "reading_value": 23.5},
                     ...
                 ]
             }
         }
      }

    Returns:
      A dictionary with the computed summary statistics and an alert message.
    """
    # Parse sensor_data if provided as a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Aggregate readings for the specified sensor_key across all sensor IDs.
    aggregated_readings = []
    for sensor_id, sensor_types in sensor_data.items():
        if sensor_key in sensor_types:
            readings = sensor_types[sensor_key].get("timeseries_data", [])
            aggregated_readings.extend(readings)

    if not aggregated_readings:
        return {"error": f"No data found for {sensor_key}"}

    try:
        df = pd.DataFrame(aggregated_readings)
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")
        latest = float(df.iloc[-1]["reading_value"])
        summary = {
            "mean": float(df["reading_value"].mean()),
            "min": float(df["reading_value"].min()),
            "max": float(df["reading_value"].max()),
            "std": float(df["reading_value"].std()),
            "latest": latest,
        }
        summary["alert"] = (
            "Temperature out of range"
            if (latest < acceptable_range[0] or latest > acceptable_range[1])
            else "Temperature normal"
        )
        return summary
    except Exception as e:
        logging.error(f"Error analyzing temperatures: {e}")
        return {"error": "Failed to analyze temperatures"}


def analyze_humidity(
    sensor_data, sensor_key="Zone_Air_Humidity_Sensor", acceptable_range=(30, 60)
):
    """
    Analyzes humidity sensor data from a nested JSON structure.

    Aggregates readings for the specified sensor_key across sensor IDs,
    computes summary statistics (mean, min, max, std, latest reading), and
    flags an alert if the latest reading is outside the acceptable range.

    Expected input (as a Python dict or JSON string):
      {
         "1": {
             "Zone_Air_Humidity_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:31:59", "reading_value": 45},
                     {"datetime": "2025-02-10 05:32:11", "reading_value": 50},
                     ...
                 ]
             },
             "Other_Sensor": { ... }
         },
         "2": {
             "Zone_Air_Humidity_Sensor": {
                 "timeseries_data": [
                     {"datetime": "2025-02-10 05:35:00", "reading_value": 55},
                     {"datetime": "2025-02-10 05:35:12", "reading_value": 60},
                     ...
                 ]
             }
         }
      }

    Returns:
      A dictionary containing summary statistics and an alert message.
    """
    # Parse sensor_data if provided as a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor_data JSON"}

    # Aggregate readings for the specified sensor_key across sensor IDs.
    aggregated_readings = []
    for sensor_id, sensor_types in sensor_data.items():
        if sensor_key in sensor_types:
            readings = sensor_types[sensor_key].get("timeseries_data", [])
            aggregated_readings.extend(readings)

    if not aggregated_readings:
        return {"error": f"No data found for {sensor_key}"}

    try:
        df = pd.DataFrame(aggregated_readings)
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")
        latest = float(df.iloc[-1]["reading_value"])
        summary = {
            "mean": float(df["reading_value"].mean()),
            "min": float(df["reading_value"].min()),
            "max": float(df["reading_value"].max()),
            "std": float(df["reading_value"].std()),
            "latest": latest,
        }
        summary["alert"] = (
            "Humidity out of range"
            if (latest < acceptable_range[0] or latest > acceptable_range[1])
            else "Humidity normal"
        )
        return summary
    except Exception as e:
        logging.error(f"Error analyzing humidity: {e}")
        return {"error": "Failed to analyze humidity"}


def analyze_temperature_humidity(
    sensor_data,
    temp_key="Air_Temperature_Sensor",
    humidity_key="Zone_Air_Humidity_Sensor",
    temp_range=(18, 27),
    humidity_range=(30, 60),
):
    """
    Analyzes temperature and humidity sensor data from a nested JSON structure.

    Aggregates readings for the specified sensor keys across sensor IDs,
    computes individual summaries for temperature and humidity, and calculates
    a combined comfort index. The comfort index is computed by measuring how
    close the latest sensor readings are to the midpoints of the acceptable ranges.

    Parameters:
      - sensor_data: A dict or JSON string in the nested format.
      - temp_key: Sensor key for temperature (default: "Air_Temperature_Sensor").
      - humidity_key: Sensor key for humidity (default: "Zone_Air_Humidity_Sensor").
      - temp_range: Acceptable range for temperature (default: (18, 27)).
      - humidity_range: Acceptable range for humidity (default: (30, 60)).

    Returns:
      A dictionary with:
        - 'temperature': Summary from analyze_temperatures.
        - 'humidity': Summary from analyze_humidity.
        - 'comfort_index': A value between 0 and 100.
        - 'comfort_assessment': A qualitative assessment ("Comfortable", "Less comfortable", or "Uncomfortable").
    """
    # Parse sensor_data if it's a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {"error": "Invalid sensor data"}

    # Call the updated analysis functions (which expect the nested JSON structure)
    temp_summary = analyze_temperatures(
        sensor_data, sensor_key=temp_key, acceptable_range=temp_range
    )
    humidity_summary = analyze_humidity(
        sensor_data, sensor_key=humidity_key, acceptable_range=humidity_range
    )

    # Compute midpoints for the acceptable ranges.
    temp_mid = (temp_range[0] + temp_range[1]) / 2.0
    humidity_mid = (humidity_range[0] + humidity_range[1]) / 2.0

    try:
        temp_latest = temp_summary.get("latest", temp_mid)
        humidity_latest = humidity_summary.get("latest", humidity_mid)
        # Calculate deviations from the midpoints.
        temp_diff = abs(temp_latest - temp_mid)
        humidity_diff = abs(humidity_latest - humidity_mid)
        # Compute a simple comfort index: 100 minus weighted deviations.
        comfort_index = 100 - (temp_diff * 2 + humidity_diff * 1.5)
        # Ensure the index is within 0 to 100.
        comfort_index = max(0, min(100, comfort_index))
        comfort_index = float(comfort_index)
    except Exception as e:
        logging.error(f"Error computing comfort index: {e}")
        comfort_index = None

    combined = {
        "temperature": temp_summary,
        "humidity": humidity_summary,
        "comfort_index": comfort_index,
        "comfort_assessment": (
            "Comfortable"
            if comfort_index is not None and comfort_index > 70
            else (
                "Less comfortable"
                if comfort_index is not None and comfort_index > 40
                else "Uncomfortable"
            )
        ),
    }
    return combined


def detect_potential_failures(sensor_data, time_window_hours=24, anomaly_threshold=3):
    """
    Detects potential sensor failures based on anomaly detection within a specified time window,
    using a nested JSON structure.

    Args:
      - sensor_data (dict or JSON string): Nested dictionary containing sensor time series data.
          Expected format:
          {
              "1": {
                  "Sensor_Type_A": {
                      "timeseries_data": [
                          {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                          {"datetime": "2025-02-10 05:32:11", "reading_value": 28.1},
                          ...
                      ]
                  },
                  "Sensor_Type_B": { ... }
              },
              "2": {
                  "Sensor_Type_A": { ... },
                  ...
              }
          }
      - time_window_hours (int): Time window in hours to analyze for potential failures.
      - anomaly_threshold (float): Z-score threshold for anomaly detection.

    Returns:
      - List of flattened sensor identifiers (e.g. "1_Sensor_Type_A") showing potential failures.
    """
    # Parse sensor_data from JSON string if necessary.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return []

    sensors_with_failures = []

    # Iterate over each sensor ID.
    for sensor_id, sensor_types in sensor_data.items():
        # Iterate over each sensor type within this sensor ID.
        for sensor_type, sensor_info in sensor_types.items():
            data_points = sensor_info.get("timeseries_data", [])
            # If there is no data, skip this sensor type.
            if not data_points:
                continue
            try:
                df = pd.DataFrame(data_points)
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp")

                # Calculate rolling mean and standard deviation for anomaly detection.
                df["rolling_mean"] = (
                    df["reading_value"].rolling(window=5, min_periods=1).mean()
                )
                df["rolling_std"] = (
                    df["reading_value"].rolling(window=5, min_periods=1).std()
                )

                # Replace zeros in rolling_std with 1 to avoid division by zero.
                std_series = df["rolling_std"].replace(0, 1)
                df["zscore"] = np.abs(
                    (df["reading_value"] - df["rolling_mean"]) / std_series
                )

                # Identify potential failures where z-score exceeds the threshold.
                potential_failures = df[df["zscore"] > anomaly_threshold]

                if not potential_failures.empty:
                    latest_timestamp = df.iloc[-1]["timestamp"]
                    failures_in_window = potential_failures[
                        potential_failures["timestamp"]
                        >= (latest_timestamp - pd.Timedelta(hours=time_window_hours))
                    ]
                    if not failures_in_window.empty:
                        sensors_with_failures.append(f"{sensor_id}_{sensor_type}")
            except Exception as e:
                logging.error(
                    f"Error processing sensor {sensor_id} ({sensor_type}): {e}"
                )

    return sensors_with_failures


def forecast_downtimes(sensor_data):
    """
    Forecast potential downtimes using predictive analytics from a nested JSON structure.

    Args:
      - sensor_data (dict or JSON string): Nested sensor data, where each outer key is a sensor ID
        and each inner key is a sensor type containing a "timeseries_data" list.
        Example:
          {
              "1": {
                  "Sensor_Type_A": {
                      "timeseries_data": [
                          {"datetime": "2025-02-10 05:31:59", "reading_value": 27.99},
                          {"datetime": "2025-02-10 05:32:11", "reading_value": 28.1},
                          ...
                      ]
                  },
                  "Sensor_Type_B": { ... }
              },
              "2": {
                  "Sensor_Type_A": { ... },
                  ...
              }
          }
      - The function forecasts downtimes based on rolling statistics.

    Returns:
      - A dictionary mapping each flattened sensor identifier (e.g. "1_Sensor_Type_A") to a list of timestamps
        (as strings) forecasted for potential downtimes.
    """
    # Parse sensor_data if it is a JSON string.
    if isinstance(sensor_data, str):
        try:
            sensor_data = json.loads(sensor_data)
        except Exception as e:
            logging.error(f"Error parsing sensor_data JSON: {e}")
            return {}

    downtimes_forecast = {}

    # Iterate over each sensor ID.
    for sensor_id, sensor_types in sensor_data.items():
        # Iterate over each sensor type for this sensor ID.
        for sensor_type, sensor_info in sensor_types.items():
            timeseries_data = sensor_info.get("timeseries_data", [])
            unique_key = f"{sensor_id}_{sensor_type}"

            if not timeseries_data:
                downtimes_forecast[unique_key] = []
                continue

            try:
                df = pd.DataFrame(timeseries_data)
                # Rename "datetime" column to "timestamp" if present.
                if "datetime" in df.columns:
                    df = df.rename(columns={"datetime": "timestamp"})
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp")
                df = df.set_index("timestamp")

                # Calculate rolling mean and standard deviation.
                df["rolling_mean"] = (
                    df["reading_value"].rolling(window=5, min_periods=1).mean()
                )
                df["rolling_std"] = (
                    df["reading_value"].rolling(window=5, min_periods=1).std()
                )

                # Define a threshold series: rolling_mean - 2 * rolling_std.
                threshold_series = df["rolling_mean"] - 2 * df["rolling_std"]
                potential_downtimes = df[df["reading_value"] < threshold_series]

                # Extract timestamps of potential downtimes.
                forecasted = potential_downtimes.index.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ).tolist()
                downtimes_forecast[unique_key] = forecasted
            except Exception as e:
                logging.error(
                    f"Error forecasting downtimes for sensor {unique_key}: {e}"
                )
                downtimes_forecast[unique_key] = []

    return downtimes_forecast


# ---------------------------
# Generic Dispatcher Endpoint
# ---------------------------

analysis_functions = {
    "analyze_recalibration_frequency": analyze_recalibration_frequency,
    "analyze_failure_trends": analyze_failure_trends,
    "analyze_device_deviation": analyze_device_deviation,
    "analyze_sensor_status": analyze_sensor_status,
    "analyze_air_quality_trends": analyze_air_quality_trends,
    "analyze_hvac_anomalies": analyze_hvac_anomalies,
    "analyze_supply_return_temp_difference": analyze_supply_return_temp_difference,
    "analyze_air_flow_variation": analyze_air_flow_variation,
    "analyze_sensor_trend": analyze_sensor_trend,
    "aggregate_sensor_data": aggregate_sensor_data,
    "correlate_sensors": correlate_sensors,
    "compute_air_quality_index": compute_air_quality_index,
    "generate_health_alerts": generate_health_alerts,
    "detect_anomalies": detect_anomalies,
    "analyze_noise_levels": analyze_noise_levels,
    "analyze_air_quality": analyze_air_quality,
    "analyze_formaldehyde_levels": analyze_formaldehyde_levels,
    "analyze_co2_levels": analyze_co2_levels,
    "analyze_pm_levels": analyze_pm_levels,
    "analyze_temperatures": analyze_temperatures,
    "analyze_humidity": analyze_humidity,
    "analyze_temperature_humidity": analyze_temperature_humidity,
    "detect_potential_failures": detect_potential_failures,
    "forecast_downtimes": forecast_downtimes,
}

@analytics_service.route("/test", methods=["GET", "POST"])
def test_endpoint():
    if request.method == "POST":
        data = request.get_json()
        return jsonify({"received Json data" : data, "status": "ok"})
    else:
        return jsonify({"status": "ok", "message": "Analytics service is running"})

@analytics_service.route("/run", methods=["POST"])
def run_analysis():
    logging.info("Analytics /run endpoint called")
    data = request.get_json()
    
    if not data or "analysis_type" not in data:
        logging.error("Missing required parameter: analysis_type")
        return jsonify({"error": "Missing required parameter: analysis_type"}), 400

    analysis_type = data["analysis_type"]
    logging.info(f"Analysis type: {analysis_type}")
    
    # Remove 'analysis_type' to isolate sensor data
    sensor_data = {k: v for k, v in data.items() if k != "analysis_type"}
    logging.info(f"Extracted sensor data keys: {list(sensor_data.keys())}")

    if not sensor_data:
        logging.error("No sensor data provided")
        return jsonify({"error": "No sensor data provided"}), 400

    if analysis_type not in analysis_functions:
        logging.error(f"Unknown analysis type: {analysis_type}")
        return jsonify({"error": f"Unknown analysis type: {analysis_type}"}), 400

    try:
        logging.info(f"Calling analysis function: {analysis_type} with data of length: {len(str(sensor_data))}")
        result = analysis_functions[analysis_type](sensor_data)
        
        # Create an enhanced response that includes the analytics type
        enhanced_result = {
            "analysis_type": analysis_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": result
        }
        
        logging.info(f"Analysis result: {enhanced_result}")
        return jsonify(enhanced_result)
    except Exception as e:
        logging.error(f"Error running analysis {analysis_type}: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({"error": f"Error running analysis {analysis_type}: {str(e)}"}), 500