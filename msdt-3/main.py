import json
import csv
import re

from checksum import calculate_checksum
from paths import CSV, REGULAR, RESULT


def read_json(path: str) -> dict:
    """
    reads a json file
    """
    try:
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        raise e


def read_csv(path: str) -> list[list[str]]:
    """
    reads a csv file 
    """
    try:
        file_data = []
        with open(path, "r", encoding="utf-16") as file:
            file_reader = csv.reader(file, delimiter=';')
            next(file_reader, None)
            for row in file_reader:
                file_data.append(row)
            return file_data
    except Exception as e:
        raise e


def write_json_file(path: str, data: dict) -> None:
    """
    writes to json
    """
    try:
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(data, file)
    except Exception as e:
        raise e


def validate_data(data: list[list[str]], regex: dict) -> list[int]:
    """
    checks the strings from the csv file for compliance with regular expressions
    """
    invalid_rows = []

    for row_number, row in enumerate(data):
        for _, (field, key) in enumerate(zip(row, regex.keys())):
            pattern = regex[key]
            if not re.fullmatch(pattern, field):
                invalid_rows.append(row_number)
                break

    return invalid_rows


if __name__ == "__main__":
    file = read_csv(CSV)
    regular = read_json(REGULAR)
    invalid_rows = validate_data(file, regular)
    summ = calculate_checksum(invalid_rows)
    result = {
        "variant": 25,
        "checksum": summ
    }
    write_json_file(RESULT, result)

