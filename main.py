import camelot
import re
import json
import requests
from datetime import datetime
import os
import sys

disricts = [
    {"name": "Thiruvananthapuram", "alt": ["Thiriruvanathapuram"]},
    {"name": "Kollam", "alt": []},
    {"name": "Pathanamthitta", "alt": []},
    {"name": "Idukki", "alt": []},
    {"name": "Kottayam", "alt": []},
    {"name": "Alappuzha", "alt": []},
    {"name": "Ernakulam", "alt": []},
    {"name": "Thrissur", "alt": []},
    {"name": "Palakkad", "alt": []},
    {"name": "Malappuram", "alt": []},
    {"name": "Kozhikode", "alt": []},
    {"name": "Wayanad", "alt": []},
    {"name": "Kannur", "alt": ["Kannu"]},
    {"name": "Kasaragod", "alt": ["Kasargod"]},
]


def parse(url):
    tables = camelot.read_pdf(url, pages="all")
    surv, chro, dist = 0, [], []
    for table in tables:
        if len(table.df.columns) in [2, 3]:
            dist.append(table.df)
        if len(table.df.columns) in [4, 5]:
            if table.df[len(table.df.columns) - 1][0] == "Remarks":
                chro.append(table.df)
            if table.df[0][0] == "District":
                surv = table.df
    data = init_data()
    num, rem, dis = "", "", ""

    # manual fixes
    # for bule_25032020.pdf
    if "bule_25032020" in url:
        chro[0][2][4] = "Pathanamthitta – 4\nKottayam – 2 \nErnakulam -2"
    # for bule_20032020.pdf
    if "bule_20032020" in url:
        chro[0][1][9] = "Thiruvananthapuram -3"
        chro[0][1][10] = "Thiruvananthapuram -1"

    # Parses table: Chronology of Positive cases
    i = 1
    if "patient" in chro[0][0][0]:
        i = 0

    def dis_parse(s):
        return list(
            map(
                re.compile("[-–]").split,
                re.sub(
                    "[\(\[].*?[\)\]]",
                    "",
                    s.replace(" ", "").replace(",", ""),
                    flags=re.DOTALL,
                ).splitlines(),
            )
        )

    def add(n):
        data[t[0]]["corona_positive"] += n
        if "Negative" in rem:
            data[t[0]]["cured_discharged"] += n
        if "Expired" in status:
            data[t[0]]["deaths"] += n

    for ch in chro:
        for row in ch.iterrows():
            if "persons have been" in row[1][0]:
                continue
            if "patient" in row[1][i]:
                continue
            if row[1][i].isnumeric():
                num = int(row[1][i])
            if row[1][i + 1]:
                dis = dis_parse(row[1][i + 1])
            else:
                continue
            if row[1][i + 2]:
                rem = row[1][i + 2]
            status = row[1][i + 3]
            if len(dis) > 1:
                if len(dis[0]) > 1:
                    for t in dis:
                        t[0] = check_alt(t[0])
                        add(int(t[1]))
                else:
                    for t in dis:
                        t[0] = check_alt(t[0])
                        add(1)
            else:
                if len(dis[0]) > 1:
                    for t in dis:
                        t[0] = check_alt(t[0])
                        add(int(t[1]))

                else:
                    t = dis[0]
                    t[0] = check_alt(t[0])
                    inc = 1
                    if row[1][i]:
                        inc = int(num)
                    add(inc)

    # Parses table: Details of persons under Surveillance
    for row in surv.iterrows():
        if any(x in row[1][0] for x in ["District", "Total"]):
            continue
        t = check_alt(row[1][0].strip())
        data[t]["under_observation"] += int(row[1][1])
        data[t]["under_home_isolation"] += int(row[1][2])
        data[t]["total_hospitalised"] += int(row[1][3])
        data[t]["hospitalised_today"] += int(row[1][4])

    # Parses table: District wise distribution based on hospital admission
    for di in dist:
        for row in di.iterrows():
            if any(x in row[1][0] for x in ["District", "Total"]):
                continue
            t = check_alt(row[1][0].strip())
            data[t]["positive_admitted"] += int(row[1][1])

    data = {
        "kerala": data,
        "time": datetime.now().isoformat(),
        "file_url": url,
    }
    return json.dumps(data)


def init_data():
    data = {}
    for d in disricts:
        data[d["name"]] = {
            "under_observation": 0,
            "under_home_isolation": 0,
            "total_hospitalised": 0,
            "hospitalised_today": 0,
            "corona_positive": 0,
            "cured_discharged": 0,
            "deaths": 0,
            "positive_admitted": 0,
        }
    return data


def check_alt(dist):
    for d in disricts:
        if dist in d["alt"]:
            return d["name"]
    return dist


if __name__ == "__main__":
    url = sys.argv[1]
    print(parse(url))
