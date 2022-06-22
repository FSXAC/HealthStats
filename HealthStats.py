import argparse

from HealthDataExtractor import *


# Setup argument parser
parser = argparse.ArgumentParser(description='Extract and visualize health data from Apple Health')
parser.add_argument('input', help='input file to the export.xml')
parser.add_argument('-o', '--output', help='output directory for the CSV files', default='data')

# Parse arguments
args = parser.parse_args()

def main():
    # Create a HealthDataExtractor object
    extractor = HealthDataExtractor(args.input)

    # Write the data to CSV files
    extractor.extract()

    # Print the data
    print(extractor)


if __name__ == '__main__':
    main()
