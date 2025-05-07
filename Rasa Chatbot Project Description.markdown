# Rasa Chatbot Project Description

## Overview
This document describes a Rasa-based chatbot project for sensor data analytics, deployed using Docker Compose. The chatbot allows users to request analytics for specific sensors over a date range, validates inputs, queries a MySQL database, calls an analytics microservice, replaces UUIDs with sensor names, and generates summaries using an LLM. The project integrates with a SPARQL endpoint for sensor metadata and uses text files for sensor validation and UUID mappings.

This description is intended to be provided to Grok (xAI's AI assistant) for future improvements. When submitting, paste this document and specify the desired changes (e.g., "This is my project. Now add a new feature to export analytics results as CSV"). The document includes all necessary details to avoid re-explaining the setup.

## Project Goals
- **User Interaction**: Accept user queries like "Give me basic sensor analytics for sensor Air_Quality_level_Sensor_5.01 from 02/02/2025 to 05/02/2025."
- **Input Validation**: Validate sensor type, start date, and end date using a Rasa form (`analysis_form`).
- **Data Retrieval**: Query a MySQL database (`sensordb.sensor_data`) using sensor UUIDs (`timeseries_id`).
- **Analytics**: Send SQL results to an analytics microservice (`http://microservices:6000/analytics/run`) for processing.
- **UUID Replacement**: Replace UUIDs in analytics responses with human-readable sensor names using `sensor_mappings.txt`.
- **Summarization**: Generate user-friendly summaries using an LLM endpoint (`https://deep-gator-cleanly.ngrok-free.app/summarize`).
- **Deployment**: Run in a Dockerized environment with Rasa, action server, MySQL, and microservices.

## System Architecture
- **Frontend**: Rasa Webchat (assumed, to be confirmed) for user interaction.
- **Backend**:
  - **Rasa Core**: Handles dialogue management and intent classification.
  - **Rasa Action Server**: Executes custom actions (`actions.py`) for validation, SQL queries, analytics, and summarization.
  - **MySQL Database**: Stores sensor data in `sensordb.sensor_data` with columns as UUIDs (e.g., `26f2c139-f60c-49dd-b3aa-2a38215123ab`).
  - **Analytics Microservice**: Processes sensor data and returns analytics (e.g., mean, std).
  - **SPARQL Endpoint**: Provides sensor metadata (UUIDs) via `http://sparql:7200/repositories/your_repo`.
  - **LLM Endpoint**: Generates summaries from analytics results.
- **Deployment**: Docker Compose with services for Rasa, action server, MySQL, and microservices.

## File Structure
The project is organized as follows:
```
project_root/
├── actions/
│   ├── actions.py              # Custom actions for validation, SQL queries, analytics, and summarization
│   ├── sensor_mappings.txt     # Sensor type to UUID mappings (e.g., "Air_Quality_level_Sensor_5.01,26f2c139-f60c-49dd-b3aa-2a38215123ab")
├── data/
│   ├── rules.yml               # Rasa rules for dialogue flow
│   ├── stories.yml             # Rasa stories for training
├── domain.yml                  # Rasa domain with intents, slots, forms, and responses
├── docker-compose.yml          # Docker Compose configuration
├── config.yml                 # Rasa configuration (assumed, not provided)
├── endpoints.yml              # Rasa endpoints (assumed, not provided)
```

### Key Files
1. **actions.py**:
   - Contains `ValidateAnalysisForm` and `ActionPerformAnalysis` classes.
   - Validates `sensor_type`, `timeseries_id`, `start_date`, and `end_date`.
   - Queries MySQL, calls analytics service, replaces UUIDs, and summarizes results.
   - Loads `sensor_mappings.txt` for UUID-to-sensor-type mappings.

2. **sensor_mappings.txt**:
   - Located in `./actions/` (mounted to `/app/actions/` in Docker).
   - Format: Comma-separated lines (e.g., `Air_Quality_level_Sensor_5.01,26f2c139-f60c-49dd-b3aa-2a38215123ab`).
   - Example:
     ```
     Air_Quality_level_Sensor_5.01,26f2c139-f60c-49dd-b3aa-2a38215123ab
     Air_Quality_level_Sensor_5.02,249a4c9c-fe31-4649-a119-452e5e8e7dc5
     Air_Quality_level_Sensor_5.03,18ca2f90-00a4-42f2-af45-725b56a828b4
     Air_Quality_level_Sensor_5.04,493a480c-84c8-4c41-b31b-b484bf170256
     ```

3. **domain.yml**:
   - Defines intents: `greet`, `goodbye`, `mood_great`, `mood_unhappy`, `affirm`, `deny`, `bot_challenge`, `test_action_server`, `Questions_to_brickbot`, `provide_sensor_type`, `provide_start_date`, `provide_end_date`, `restart`, `cancel`.
   - Slots: `sensor_type` (text), `timeseries_id` (text, internal), `start_date` (text), `end_date` (text).
   - Form: `analysis_form` with required slots (`sensor_type`, `timeseries_id`, `start_date`, `end_date`).
   - Responses: `utter_greet`, `utter_goodbye`, `utter_iamabot`, etc.

4. **rules.yml**:
   - Rules for activating/submitting `analysis_form`, handling interruptions (`greet`, `cancel`), and restarting conversations.

5. **stories.yml**:
   - Training stories for happy path, sad path, bot challenge, and form completion scenarios.

6. **docker-compose.yml** (assumed):
   ```yaml
   version: '3'
   services:
     rasa:
       image: rasa/rasa:3.6.0
       ports:
         - "5005:5005"
       volumes:
         - ./:/app
       command: run --enable-api --debug
     rasa_action_server:
       image: rasa/rasa:3.6.0
       ports:
         - "5055:5055"
       volumes:
         - ./actions:/app/actions
       environment:
         - DB_HOST=10.98.40.96
         - DB_NAME=sensordb
         - DB_USER=root
         - DB_PASSWORD=root
         - DB_PORT=3306
         - SPARQL_ENDPOINT=http://sparql:7200/repositories/your_repo
         - NL2SPARQL_URL=https://deep-gator-cleanly.ngrok-free.app/nl2sparql
         - STATIC_FOLDER=/app/actions/static/attachments
         - BASE_URL=http://localhost:8000
       command: run actions --debug
     mysql:
       image: mysql:8.0
       environment:
         - MYSQL_ROOT_PASSWORD=root
       ports:
         - "3306:3306"
     microservices:
       image: custom-analytics-service  # Placeholder
       ports:
         - "6000:6000"
     sparql:
       image: ontotext/graphdb:10.0.0  # Placeholder
       ports:
         - "7200:7200"
   ```

## Functional Workflow
1. **User Input**:
   - Example: "Can you give me basic sensor analytics for sensor Air_Quality_level_Sensor_5.01 starts from 02/02/2025 until ends on 05/02/2025?"
   - Intent: `Questions_to_brickbot`.
   - Entities: `sensor_type`, `time` (with `start` and `end` roles).

2. **Form Validation (`ValidateAnalysisForm`)**:
   - Activates `analysis_form` to collect `sensor_type`, `timeseries_id`, `start_date`, `end_date`.
   - **validate_sensor_type**:
     - Loads `sensor_mappings.txt` to map sensor types to UUIDs.
     - Validates `sensor_type` (e.g., `Air_Quality_level_Sensor_5.01`).
     - Sets `sensor_type` and `timeseries_id` (e.g., `26f2c139-f60c-49dd-b3aa-2a38215123ab`).
     - Prompts for valid input if invalid (e.g., "Invalid sensor type: Invalid_Sensor").
   - **validate_timeseries_id**: Confirms `timeseries_id` is set.
   - **validate_start_date/end_date**:
     - Parses dates using `dateutil.parser` and regex.
     - Ensures `end_date` is after `start_date`.
     - Formats as `YYYY-MM-DD HH:MM:SS` (e.g., `2025-02-02 00:00:00`).

3. **Analytics (`ActionPerformAnalysis`)**:
   - **SQL Query**:
     - Connects to MySQL (`10.98.40.96:3306`, `sensordb`, `root/root`).
     - Queries `sensordb.sensor_data` using `timeseries_id` (e.g., `SELECT Datetime, `26f2c139-f60c-49dd-b3aa-2a38215123ab` ...`).
     - Returns a Pandas DataFrame.
   - **Analytics Service**:
     - Sends SQL results to `http://microservices:6000/analytics/run` with `analysis_type="basic_statistics"`.
     - Payload: `{"analysis_type": "basic_statistics", "sensor_data": [...]}`.
     - Response example:
       ```json
       {
         "timeseries_ids": ["26f2c139-f60c-49dd-b3aa-2a38215123ab"],
         "results": {
           "26f2c139-f60c-49dd-b3aa-2a38215123ab": {
             "mean": 10.5,
             "std": 1.2
           }
         }
       }
       ```
   - **UUID Replacement**:
     - Loads `sensor_mappings.txt` to create a UUID-to-sensor-type mapping.
     - Recursively replaces UUIDs in `analytics_response` with sensor types (e.g., `26f2c139-f60c-49dd-b3aa-2a38215123ab` → `Air_Quality_level_Sensor_5.01`).
     - Modified response:
       ```json
       {
         "timeseries_ids": ["Air_Quality_level_Sensor_5.01"],
         "results": {
           "Air_Quality_level_Sensor_5.01": {
             "mean": 10.5,
             "std": 1.2
           }
         }
       }
       ```
   - **Summarization**:
     - Sends modified `analytics_response` to `https://deep-gator-cleanly.ngrok-free.app/summarize`.
     - Payload: `{"analytics_data": {...}}`.
     - Expects: `{"summary": "Air_Quality_level_Sensor_5.01 shows stable readings..."}`.
     - Displays analytics results and summary to the user.

4. **Output**:
   - Example:
     ```
     Analytics results:
     {
       "timeseries_ids": ["Air_Quality_level_Sensor_5.01"],
       "results": {
         "Air_Quality_level_Sensor_5.01": {
           "mean": 10.5,
           "std": 1.2
         }
       }
     }
     Summary: Air_Quality_level_Sensor_5.01 shows stable readings...
     ```

## Dependencies
- **Rasa**: `rasa==3.6.0`
- **Python Libraries** (in `actions.py`):
  - `mysql-connector-python`
  - `pandas`
  - `requests`
  - `python-dateutil`
  - `re`
  - `logging`
  - `json`
- **Docker Images**:
  - `rasa/rasa:3.6.0`
  - `mysql:8.0`
  - `ontotext/graphdb:10.0.0` (assumed for SPARQL)
  - Custom analytics service (assumed)
- **External Services**:
  - MySQL: `10.98.40.96:3306`, `sensordb`, `root/root`
  - Analytics: `http://microservices:6000/analytics/run`
  - SPARQL: `http://sparql:7200/repositories/your_repo`
  - LLM: `https://deep-gator-cleanly.ngrok-free.app/summarize`

## Database Schema
- **Database**: `sensordb`
- **Table**: `sensor_data`
- **Columns**:
  - `Datetime`: Timestamp (e.g., `2025-02-02 00:00:00`)
  - Sensor UUIDs (e.g., `26f2c139-f60c-49dd-b3aa-2a38215123ab`): Numeric sensor readings
- Example:
  ```sql
  DESCRIBE sensordb.sensor_data;
  +--------------------------------------+-------------+
  | Field                                | Type        |
  +--------------------------------------+-------------+
  | Datetime                             | datetime    |
  | 26f2c139-f60c-49dd-b3aa-2a38215123ab | float       |
  | 249a4c9c-fe31-4649-a119-452e5e8e7dc5 | float       |
  +--------------------------------------+-------------+
  ```

## SPARQL Integration
- **Endpoint**: `http://sparql:7200/repositories/your_repo`
- **Purpose**: Provides sensor UUIDs matching `sensor_mappings.txt`.
- **Usage**: Not directly queried in `actions.py` (assumed to populate `sensor_mappings.txt`).

## Deployment Instructions
1. **Prepare Files**:
   - Ensure `sensor_mappings.txt` exists in `./actions/`:
     ```bash
     cat <<EOT > actions/sensor_mappings.txt
     Air_Quality_level_Sensor_5.01,26f2c139-f60c-49dd-b3aa-2a38215123ab
     Air_Quality_level_Sensor_5.02,249a4c9c-fe31-4649-a119-452e5e8e7dc5
     Air_Quality_level_Sensor_5.03,18ca2f90-00a4-42f2-af45-725b56a828b4
     Air_Quality_level_Sensor_5.04,493a480c-84c8-4c41-b31b-b484bf170256
     EOT
     chmod 644 actions/sensor_mappings.txt
     ```

2. **Start Containers**:
   ```bash
   docker-compose up -d
   ```

3. **Train Model**:
   ```bash
   docker-compose exec rasa rasa train
   ```

4. **Test**:
   ```bash
   docker-compose exec rasa rasa shell
   ```
   - Input: `can you give me basic sensor analytics for sensor Air_Quality_level_Sensor_5.01 starts from 02/02/2025 until ends on 05/02/2025?`
   - Check logs:
     ```bash
     docker-compose logs rasa_action_server
     ```

## Testing Scenarios
1. **Valid Input**:
   - Input: `can you give me basic sensor analytics for sensor Air_Quality_level_Sensor_5.01 starts from 02/02/2025 until ends on 05/02/2025?`
   - Expected:
     - Slots: `sensor_type="Air_Quality_level_Sensor_5.01"`, `timeseries_id="26f2c139-f60c-49dd-b3aa-2a38215123ab"`, `start_date="2025-02-02 00:00:00"`, `end_date="2025-02-05 23:59:59"`.
     - SQL query with `timeseries_id`.
     - Analytics response with sensor types.
     - Summary with sensor names.

2. **Invalid Sensor**:
   - Input: `can you give me basic sensor analytics for sensor Invalid_Sensor`
   - Expected: `Invalid sensor type: Invalid_Sensor. Please provide a valid sensor (e.g., Air_Quality_level_Sensor_5.01).`

3. **Missing Data**:
   - Input: `can you give me basic sensor analytics`
   - Expected: `Please provide a valid sensor type.`

## Troubleshooting
1. **FileNotFoundError for `sensor_mappings.txt`**:
   - Verify: `ls -l actions/sensor_mappings.txt`
   - Fix: Recreate file (see above).
   - Check Docker volume:
     ```bash
     docker inspect <project>_rasa_action_server_1 | grep -A 5 '"Mounts":'
     ```

2. **MySQL Errors**:
   - Test: `mysql -h 10.98.40.96 -u root -p -P 3306 -e "SELECT * FROM sensordb.sensor_data LIMIT 1;"`
   - Fix: Verify credentials, ensure table/columns exist.

3. **Analytics Service Errors**:
   - Test: `curl -X POST http://microservices:6000/analytics/run -H "Content-Type: application/json" -d '{"analysis_type": "basic_statistics", "sensor_data": []}'`
   - Fix: Check service logs, verify endpoint.

4. **Summarization Errors**:
   - Test: `curl -X POST https://deep-gator-cleanly.ngrok-free.app/summarize -H "Content-Type: application/json" -d '{"analytics_data": {"timeseries_ids": ["Air_Quality_level_Sensor_5.01"]}}'`
   - Fix: Update endpoint/payload in `actions.py`.

## Security Notes
- **MySQL Credentials**: Replace `root/root` with secure credentials:
  ```sql
  CREATE USER 'rasa_user'@'10.98.40.%' IDENTIFIED BY 'secure_password';
  GRANT SELECT ON sensordb.sensor_data TO 'rasa_user'@'10.98.40.%';
  ```
  Update `docker-compose.yml`:
  ```yaml
  environment:
    - DB_USER=rasa_user
    - DB_PASSWORD=secure_password
  ```
- **File Permissions**: Ensure `sensor_mappings.txt` is readable (`chmod 644`).
- **Network**: Restrict MySQL (`10.98.40.96:3306`) to internal network.

## Assumptions
- **UI**: Rasa Webchat (to be confirmed).
- **Analytics Service**: Custom microservice, JSON-based.
- **LLM Endpoint**: JSON-based, expects `{"analytics_data": {...}}`.
- **SPARQL**: Populates `sensor_mappings.txt` offline.
- **Config Files**: `config.yml`, `endpoints.yml` exist with standard settings.

## Future Improvements
To request improvements, provide this document to Grok and specify changes, e.g.:
- "Add CSV export for analytics results."
- "Support multiple sensors in one query."
- "Integrate real-time SPARQL queries."
- "Add visualization charts to the UI."

## Contact Points
- **MySQL Host**: `10.98.40.96:3306`
- **Analytics URL**: `http://microservices:6000/analytics/run`
- **Summarization URL**: `https://deep-gator-cleanly.ngrok-free.app/summarize` (to be confirmed)
- **SPARQL Endpoint**: `http://sparql:7200/repositories/your_repo`

## Last Updated
- **Date**: April 27, 2025
- **Grok Version**: Grok 3 (xAI)

---

This document is complete and ready for reuse. Paste it into Grok when requesting improvements, followed by your specific changes. If you need clarification or additional details included, let me know before finalizing!