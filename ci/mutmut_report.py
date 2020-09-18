import subprocess
import json
import os
import csv


def create_report():
    mutmut_result = subprocess.run(["mutmut", "run", "--use-coverage"], stdout=subprocess.PIPE)

    survival_rate = extract_survival_rate(mutmut_result.stdout)
    dict_report = create_report_dict(survival_rate)

    write_json_report(dict_report)
    write_csv_report(dict_report)


def extract_survival_rate(mutmut_result):
    lines: list = mutmut_result.decode("utf-8").split("\r")
    last_line = lines[-1]
    result_elements = last_line.split()

    total_mutants = int(result_elements[1].split("/")[0])
    surviving_mutants = int(result_elements[9])
    return round((surviving_mutants / total_mutants) * 100)


def create_report_dict(survival_rate):
    return {"survival_rate": survival_rate}


def write_json_report(dict_report):
    filename = '.mutmut/mutmut_report.json'
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(json.dumps(dict_report))


def write_csv_report(dict_report):
    with open('.mutmut/mutmut_report.csv', mode='w') as mutmut_report_file:
        field_name = ['survival_rate']
        writer = csv.DictWriter(mutmut_report_file, fieldnames=field_name)

        writer.writeheader()
        writer.writerow(dict_report)


if __name__ == '__main__':
    create_report()
