"""
Extract data from Apple Health App's export.xml file.

Originally by: Nicholas J. Radcliffe Copyright (c) 2016
License: MIT

Adapted from: Mark Koester (github.com/markwk/qs_ledger)
"""

import os
import re
import sys

from xml.etree import ElementTree
from collections import Counter, OrderedDict


# Data type prefix regex
PREFIX_RE = re.compile('^HK.*TypeIdentifier(.+)$')


RECORD_FIELDS = OrderedDict((
    ('sourceName', 's'),
    ('sourceVersion', 's'),
    ('device', 's'),
    ('type', 's'),
    ('unit', 's'),
    ('creationDate', 'd'),
    ('startDate', 'd'),
    ('endDate', 'd'),
    ('value', 'n'),
))

ACTIVITY_SUMMARY_FIELDS = OrderedDict((
    ('dateComponents', 'd'),
    ('activeEnergyBurned', 'n'),
    ('activeEnergyBurnedGoal', 'n'),
    ('activeEnergyBurnedUnit', 's'),
    ('appleExerciseTime', 's'),
    ('appleExerciseTimeGoal', 's'),
    ('appleStandHours', 'n'),
    ('appleStandHoursGoal', 'n'),
))

WORKOUT_FIELDS = OrderedDict((
    ('sourceName', 's'),
    ('sourceVersion', 's'),
    ('device', 's'),
    ('creationDate', 'd'),
    ('startDate', 'd'),
    ('endDate', 'd'),
    ('workoutActivityType', 's'),
    ('duration', 'n'),
    ('durationUnit', 's'),
    ('totalDistance', 'n'),
    ('totalDistanceUnit', 's'),
    ('totalEnergyBurned', 'n'),
    ('totalEnergyBurnedUnit', 's'),
))

FIELDS = {
    'Record': RECORD_FIELDS,
    'ActivitySummary': ACTIVITY_SUMMARY_FIELDS,
    'Workout': WORKOUT_FIELDS,
}

def format_value(value, datatype):
    """
    Format a value for a CSV file, escaping double quotes and backslashes.
    None maps to empty.
    datatype should be
        's' for string (escaped)
        'n' for number
        'd' for datetime
    """
    if value is None:
        return ''
    elif datatype == 's':
        # string
        return f'"{value.replace("\\", "\\\\").replace("\"", "\\\"")}"'
    elif datatype in ('n', 'd'):
        # number or date
        return value
    else:
        raise KeyError(f'Unexpected format value: {datatype}')

def shorten_type_name(name):
    """
    Shortens particularly verbose strings based on a regular expression

    @param name: the name to shorten
    """

    m = re.match(PREFIX_RE, name)
    return m.group(1)


class HealthDataExtractor:
    """
    Extract health data from Apple Health App's XML export
    
    @param path: relative or absolute path to export.xml
    
    Outputs a CSV file for each record type found, in the same
    directory as the input export.xml.
    """

    def __init__(self, path):
        self.in_path = path
        self.directory = os.path.abspath(os.path.split(path)[0])

        # Load the xml
        with open(path, 'r') as f:
            self.data = ElementTree.parse(f)

        self.root = self.data._root
        self.nodes = list(self.root)
        self.num_nodes = len(self.nodes)

        # Shorten the data type names
        self.shorten_type_names()

        # Count the data
        self.count_record_types()
        self.count_tags_and_fields()


    def shorten_type_names(self):
        """
        Shortens the data type names by removing common boilerplate text
        """

        for node in self.nodes:
            if node.tag == 'Record':
                if 'type' in node.attrib:
                    node.attrib['type'] = shorten_type_name(node.attrib['type'])

    def count_record_types(self):
        """
        Counts occurrences of each type of (conceptual) record
        In the case of nodes of type 'Record', this counts the number of
        occurrences of each 'type' or record in self.record_types.

        In the case of nodes of type 'ActivitySummary' and 'Workout',
        it just counts those in self.other_types.

        The slightly different handling reflects that 'Record' nodes come
        in a variety of different subtypes that we want to write to
        different data files, whereas (for now) we are going to write
        all Workout entries to a single file, and all ActivitySummary
        entries to another single file.
        """

        # Initialize the counters
        self.record_types = Counter()
        self.other_types = Counter()

        # Iterate all nodes
        for record in self.nodes:
            if record.tag == 'Record':
                self.record_types[record.attrib['type']] += 1
            elif record.tag in ('ActivitySummary', 'Workout'):
                self.other_types[record.tag] += 1
            elif record.tag in ('Export', 'Me'):
                pass
            else:
                print(f'Unknown node of type: {record.tag}')

    def count_tags_and_fields(self):
        self.tags = Counter()
        self.fields = Counter()

        for record in self.nodes:
            self.tags[record.tag] += 1
            for k in record.keys():
                self.field[k] += 1

    def open_for_writing(self):
        """
        Open files for writing
        """

        self.handles = {}
        self.paths = {}

        for kind in (list(self.record_types) + list(self.other_types)):
            path = os.path.join(self.directory, f'{shorten_type_name(kind)}.csv')
            self.paths[kind] = path
            self.handles[kind] = open(path, 'w')
            header_type = kind if kind in ('Workout', 'ActivitySummary') else 'Record'
            self.handles[kind].write(','.join(FIELDS[header_type].keys()) + '\n')

    def write_record(self):
        kinds = FIELDS.keys()
        for node in self.nodes:
            if node.tag in kinds:
                attributes = node.attrib
                kind = attributes['type'] if node.tag == 'Record' else node.tag

                values = [format_value(attributes.get(field), datatype)
                          for (field, datatype) in FIELDS[node.tag].items()]
                line = f'{",".join(values)}\n'
                self.handles[kind].write(line)

    def close_files(self):
        for (kind, f) in self.handles.items():
            f.close()
            self.report('Written %s data.' % shorten_type_name(kind))

    def extract(self):
        """
        Extract the XML data to file
        """

        self.open_for_writing()
        self.write_records()
        self.close_files()

    def __str__(self) -> str:
        """
        Prints a summary of the data
        """

        s = ''

        # Helper function to append to the string given a counter
        def append_counter(s, name, counter):
            s += f'\n{name}\n'
            for key, count in counter.most_common():
                s += f'{key}: {count}\n'
        
        # Print tags
        append_counter(s, 'Tags', self.tags)

        # Print fields
        append_counter(s, 'Fields', self.fields)

        # Print record types
        append_counter(s, 'Record Types', self.record_types)

        return s

    