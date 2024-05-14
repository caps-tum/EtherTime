import argparse

from ptp_perf.utilities.django_utilities import bootstrap_django_environment

bootstrap_django_environment()

from ptp_perf.models import LogRecord, PTPProfile


def search(key: str):
    results = LogRecord.objects.filter(message__contains=key)
    for result in results:
        print(f"{result.endpoint.profile} | {result}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Search logs for a value and return the profiles associated with them.")

    parser.add_argument("search_key", type=str)

    result = parser.parse_args()

    search(result.search_key)
