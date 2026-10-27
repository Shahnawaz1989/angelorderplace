from config import CONFIG
from smartapi_service import SmartApiService


def main():
    service = SmartApiService(CONFIG)
    service.login()

    response = service.order_book()

    print("ORDER BOOK RESPONSE:")
    print(response)

    rows = response.get("data", []) if isinstance(response, dict) else []

    for row in rows:
        symbol = str(row.get("tradingsymbol", ""))

        if symbol == "CRUDEOILM17SEP268350CE":
            print("\nMATCHING ORDER:")
            print(row)


if __name__ == "__main__":
    main()
