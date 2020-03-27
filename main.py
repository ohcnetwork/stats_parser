import camelot
import re
import json
import requests
from datetime import datetime
import os


def parse_pdf(request):
    if request.args and "url" in request.args:
        url = request.args.get("url")
        tables = camelot.read_pdf(url, pages="all", flavor="lattice")
        surv, chro, dist = 0, [], 0
        for table in tables:
            if table.df[len(table.df.columns) - 1][0] == "Remarks":
                chro.append(table.df)
            if table.df[0][0] == "District":
                if len(table.df.columns) == 5:
                    surv = table.df
                if table.df[0][0] == "District":
                    dist = table.df
        # manual fix for bule_25032020.pdf
        if "bule_25032020" in url:
            chro[2][4] = "Pathanamthitta – 4\nKottayam – 2 \nErnakulam -2"
        data = {}
        disricts = [
            "Thiruvananthapuram",
            "Kollam",
            "Pathanamthitta",
            "Idukki",
            "Kottayam",
            "Alappuzha",
            "Ernakulam",
            "Thrissur",
            "Palakkad",
            "Malappuram",
            "Kozhikode",
            "Wayanad",
            "Kannur",
            "Kasaragod",
        ]
        for d in disricts:
            data[d] = {
                "under_observation": 0,
                "under_home_isolation": 0,
                "total_hospitalised": 0,
                "hospitalised_today": 0,
                "corona_positive": 0,
                "cured_discharged": 0,
                "deaths": 0,
                "positive_admitted": 0,
            }
        i = 1
        if "patient" in chro[0][0]:
            i = 0
        num = ""
        rem = ""
        dis = ""

        def remove_unwanted(s):
            return re.sub("[\(\[].*?[\)\]]", "", s.replace(" ", "").replace(",", ""))

        def dis_parse(s):
            return list(map(remove_unwanted, re.compile("[-–]").split(s)))

        for ch in chro:
            for row in ch.iterrows():
                if "persons have been" in row[1][0]:
                    continue
                if "patient" in row[1][i]:
                    continue
                if row[1][i].isnumeric():
                    num = int(row[1][i])
                if row[1][i + 1]:
                    dis = list(map(dis_parse, row[1][i + 1].splitlines()))
                else:
                    continue
                if row[1][i + 2]:
                    rem = row[1][i + 2]
                if len(dis) > 1:
                    if len(dis[0]) > 1:
                        for t in dis:
                            data[t[0]]["corona_positive"] = data[t[0]][
                                "corona_positive"
                            ] + int(t[1])
                            if "Negative" in rem:
                                data[t[0]]["cured_discharged"] = data[t[0]][
                                    "cured_discharged"
                                ] + int(t[1])
                    else:
                        for t in dis:
                            if t[0] == "Kasargod":
                                t[0] = "Kasaragod"
                            data[t[0]]["corona_positive"] = (
                                data[t[0]]["corona_positive"] + 1
                            )
                            if "Negative" in rem:
                                data[t[0]]["cured_discharged"] = (
                                    data[t[0]]["cured_discharged"] + 1
                                )
                else:
                    if len(dis[0]) > 1:
                        for t in dis:
                            data[t[0]]["corona_positive"] = data[t[0]][
                                "corona_positive"
                            ] + int(t[1])
                            if "Negative" in rem:
                                data[t[0]]["cured_discharged"] = data[t[0]][
                                    "cured_discharged"
                                ] + int(t[1])
                    else:
                        for t in dis[0]:
                            data[t]["corona_positive"] = data[t][
                                "corona_positive"
                            ] + int(num)
                            if "Negative" in rem:
                                data[t]["cured_discharged"] = data[t][
                                    "cured_discharged"
                                ] + int(num)
        for row in surv.iterrows():
            if "District" in row[1][0]:
                continue
            if "Total" in row[1][0]:
                continue
            t = row[1][0].strip()
            data[t]["under_observation"] = data[t]["under_observation"] + int(row[1][1])
            data[t]["under_home_isolation"] = data[t]["under_home_isolation"] + int(
                row[1][2]
            )
            data[t]["total_hospitalised"] = data[t]["total_hospitalised"] + int(
                row[1][3]
            )
            data[t]["hospitalised_today"] = data[t]["hospitalised_today"] + int(
                row[1][4]
            )
        for row in dist.iterrows():
            if "District" in row[1][0]:
                continue
            if "Total" in row[1][0]:
                continue
            t = row[1][0].strip()
            data[t]["positive_admitted"] = data[t]["positive_admitted"] + int(row[1][1])
        _data = {"kerala": data, "time": datetime.now().isoformat(), "file_url": url}
        test = 0
        if request.args and "test" in request.args:
            test = int(request.args.get("test"))
        if not test:
            send_res(request, _data)
        return json.dumps(_data)
    else:
        return f"No url"


def send_res(request, data):
    print(os.environ.get("WEBHOOK"))
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"Parsed <{data['file_url']}>"},
        }
    ]
    for d in data["kerala"]:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{d}:*"},}
        )
        tmp = []
        for key, value in data["kerala"][d].items():
            tmp.append({"type": "mrkdwn", "text": f"{key}:{value}"})
        blocks.append({"type": "section", "fields": tmp})
    payload = {
        "blocks": json.dumps(blocks),
        "username": "parser_bot",
        "icon_emoji": ":robot_face:",
    }
    response = requests.post(
        os.environ.get("WEBHOOK"),
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    print(response)
