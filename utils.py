import zipfile
import pandas as pd
import os
from datetime import datetime
import numpy as np
from sql_utils import get_rds_connection  # make sure sql_utils.py is in the same folder

# ========== Timestamp Cleaning ==========

def clean_timestamp_data(df):
    df["unix_timestamp_cleaned"] = df["unixTimestampInMs"] + df["timezoneOffsetInMs"]
    df["timestamp_cleaned"] = df["unixTimestampInMs"] + df["timezoneOffsetInMs"]
    df["timestamp_cleaned"] = df["timestamp_cleaned"] / 1000.0
    df["timestamp_cleaned"] = df["timestamp_cleaned"].apply(lambda ts: datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))
    df['timestamp_cleaned'] = pd.to_datetime(df['timestamp_cleaned'])
    df = df.sort_values(by='timestamp_cleaned')
    df = df.drop(columns=["unixTimestampInMs", "timezoneOffsetInMs", "isoDate"])
    columns = ['timestamp_cleaned'] + [col for col in df.columns if col != 'timestamp_cleaned']
    return df[columns]

# ========== ZIP Processing Helpers ==========

def extract_zip(zip_file_path):
    temp_dir = "temp_extracted"
    with zipfile.ZipFile(zip_file_path, 'r') as z:
        z.extractall(temp_dir)
    return temp_dir

def get_matching_directories(temp_dir, user_name):
    matching_dirs = []
    for folder in os.listdir(temp_dir):
        folder_path = os.path.join(temp_dir, folder)
        if os.path.isdir(folder_path):
            matching_dirs.append(folder_path)
    return matching_dirs

def get_binary_indicator(labfront_exported_data_path):
    binary_indicator = np.zeros(11)
    file_types = [
        "activity_details_summary", "daily_summary", "hrv_summary", "sleep_summary",
        "daily_heart_rate", "hrv_values", "respiration", "sleep_respiration",
        "sleep_stage", "stress", "epoch"
    ]
    file_types_2 = [s.replace("_", "-") for s in file_types]

    for i, file_type in enumerate(file_types):
        if os.path.exists(os.path.join(labfront_exported_data_path, f"garmin-connect-{file_type}")):
            binary_indicator[i] = 1
        if os.path.exists(os.path.join(labfront_exported_data_path, f"garmin-connect-{file_types_2[i]}")):
            binary_indicator[i] = 1
    return binary_indicator.astype(bool)

def get_csv_files_from_local(path, skiprows=5):
    csv_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.csv')]
    dfs = []
    for csv_file in csv_files:
        try:
            dfs.append(pd.read_csv(csv_file, skiprows=skiprows))
        except Exception as e:
            print(f"Error reading file {csv_file}: {e}")
    return dfs

# ========== Core Cleaning Logic ==========

def clean_data(binary_indicator, labfront_exported_data_path):
    result = {}
    file_mapping = {
        0: "activity_details_summary", 1: "daily_summary", 3: "sleep_summary",
        4: "daily_heart_rate", 6: "respiration", 7: "sleep_respiration",
        8: "sleep_stage", 9: "stress", 10: "epoch"
    }
    file_types_2 = {s: s.replace("_", "-") for _, s in file_mapping.items()}

    for idx, folder_name in file_mapping.items():
        if binary_indicator[idx]:
            folder_path = os.path.join(labfront_exported_data_path, f"garmin-connect-{folder_name}")
            if not os.path.exists(folder_path):
                folder_path = os.path.join(labfront_exported_data_path, f"garmin-connect-{file_types_2[folder_name]}")
            if not os.path.exists(folder_path):
                continue
            dfs = get_csv_files_from_local(folder_path)
            if dfs:
                combined_df = pd.concat(dfs, ignore_index=True)
                cleaned_df = clean_timestamp_data(combined_df)
                result[folder_name] = cleaned_df
    return result

# ========== Save to RDS ==========

def save_data(df_dict, user_name):
    conn = get_rds_connection()
    cursor = conn.cursor()

    for k in df_dict:
        df_dict[k]["name"] = user_name
        df_dict[k] = df_dict[k].applymap(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x)
        df_dict[k] = df_dict[k].replace({pd.NA: None, np.nan: None})

    for df_name, df in df_dict.items():
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {user_name}_{df_name} ("
        for col in df.columns:
            col_type = pd_to_sql_type(df[col].dtype)
            create_table_sql += f"{col} {col_type}, "
        create_table_sql = create_table_sql.rstrip(', ') + ")"
        cursor.execute(create_table_sql)

        columns = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_sql = f"INSERT IGNORE INTO {user_name}_{df_name} ({columns}) VALUES ({placeholders})"
        data_to_insert = [tuple(row) for row in df.itertuples(index=False, name=None)]
        cursor.executemany(insert_sql, data_to_insert)

    conn.commit()
    conn.close()

def pd_to_sql_type(pd_type):
    if pd_type == 'int64':
        return 'BIGINT'
    elif pd_type == 'float64':
        return 'REAL'
    elif pd_type == 'bool':
        return 'BOOLEAN'
    else:
        return 'TEXT'

# ========== Entry Point from FastAPI ==========

def process_local_zip(zip_file_path, user_name):
    temp_dir = extract_zip(zip_file_path)
    matching_dirs = get_matching_directories(temp_dir, user_name)
    if not matching_dirs:
        print("No matching directories found for the user.")
        return

    for idx, labfront_exported_data_path in enumerate(matching_dirs):
        binary_ind = get_binary_indicator(labfront_exported_data_path)
        cleaned_data = clean_data(binary_ind, labfront_exported_data_path)
        save_data(cleaned_data, user_name)
        print(f"✅ Cleaned and saved data for {user_name} from {labfront_exported_data_path} ({idx+1}/{len(matching_dirs)})")

    print("✅ Database successfully updated!")
