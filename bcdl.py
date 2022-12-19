import argparse
import src.scraper as sc
import logging


log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-u', '--urls',
        nargs='*', type=str, required=True,
        help='album/track url (default: %(default)s)',
    )
    parser.add_argument(
        '-w', '--workers', type=int, default=5, help='number of concurrent downloads (default: %(default)s)',
    )
    parser.add_argument(
        '-d', '--dest',  type=str, default='downloads', help='destination folder (default: %(default)s)',
    )
    args = parser.parse_args()

    sc.dl(args.urls, args.dest, args.workers)


if __name__ == '__main__':
    main()
