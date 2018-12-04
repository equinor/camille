from subprocess import check_output
from json import dumps
import os


def create_report():
    branch = "master"

    mutmut_result = check_output(["mutmut", "results"])
    survival_rate = extract_survival_rate(mutmut_result)
    json_report = create_json_report(branch, survival_rate)
    write_report(json_report)


def extract_survival_rate(mutmut_result):
    lines: list = mutmut_result.decode().split("\n")
    before_survivers = [i for i, s in enumerate(lines) if "Survived" in s]
    del lines[0:before_survivers[0]+1]

    return sum("mutmut apply" in l for l in lines)


def create_json_report(branch, survival_rate):
    dict_report = {"branches": {"branch": branch, "survival_rate": survival_rate}}

    return dumps(dict_report)


def write_report(json_report):
    filename = 'mutmut/mutmut_report.json'
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(json_report)


if __name__ == '__main__':
    create_report()

