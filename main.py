import camelot
import re
import json
import requests
from datetime import datetime
import os


def parse_pdf(request, db=False):
    test = 0
    try:
        content_type = request.headers["content-type"]
    except:
        pass
    if request.args and "url" in request.args:
        url = request.args.get("url")
        if "test" in request.args:
            test = int(request.args.get("test"))
    elif content_type == "application/json":
        request_json = request.get_json(silent=True)
        if request_json and "text" in request_json:
            url = request_json["text"]
        else:
            msg = "JSON is invalid, or missing a 'text' property"
            if not test:
                send_err_res(msg)
            raise ValueError(msg)
    else:
        msg = "No 'url' in param or wrong content type"
        if not test:
            send_err_res(msg)
        raise ValueError(msg)
    try:
        data = parse(url)
        if not test:
            send_res(request, data, db)
        if db:
            return data
        return json.dumps(data)
    except Exception as e:
        if not test:
            send_err_res(getattr(e, 'message', repr(e)))
        raise e


def parse_pdf_update(request):
    json_data = parse_pdf(request, db=True)
    # TODO do stuff here to update db
    return "Updating db..."


def parse(url):
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
    data = init_data()
    i = 1
    if "patient" in chro[0][0]:
        i = 0
    num, rem, dis = "", "", ""

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
                        data[t]["corona_positive"] = data[t]["corona_positive"] + int(
                            num
                        )
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
        data[t]["total_hospitalised"] = data[t]["total_hospitalised"] + int(row[1][3])
        data[t]["hospitalised_today"] = data[t]["hospitalised_today"] + int(row[1][4])
    for row in dist.iterrows():
        if "District" in row[1][0]:
            continue
        if "Total" in row[1][0]:
            continue
        t = row[1][0].strip()
        data[t]["positive_admitted"] = data[t]["positive_admitted"] + int(row[1][1])
    _data = {
        "kerala": data,
        "time": datetime.now().isoformat(),
        "file_url": url,
    }
    return _data


def init_data():
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
    return data


def send_res(request, data, db=False):
    webhook_url = os.environ.get("WEBHOOK")
    print(webhook_url)
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
    if db:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Updating Database...*"},
            }
        )
    payload = {
        "blocks": json.dumps(blocks),
        "username": "parser_bot",
        "icon_emoji": ":robot_face:",
    }
    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    print(response)


def send_err_res(msg):
    webhook_url = os.environ.get("WEBHOOK")
    print(webhook_url)
    payload = {
        "text": msg,
        "username": "parser_bot",
        "icon_emoji": ":robot_face:",
    }
    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    print(response)
