import site
import os.path
import sys


def add_vendor_packages(vendor_folder):
    sys.path, remainder = sys.path[:1], sys.path[1:]
    site.addsitedir(os.path.join(os.path.dirname(__file__), vendor_folder))
    sys.path.extend(remainder)

add_vendor_packages('lib')