import sys
from main import parse_pdf


class Object(object):
    pass


if __name__ == "__main__":
    url = sys.argv[1]
    request = Object()
    request.args = {"url": url,"test": "1"}
    print(f"Parsing url:{url}\n")
    res = parse_pdf(request)
    print(res)
