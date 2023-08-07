import os
import re
import argparse
from collections import defaultdict


parser = argparse.ArgumentParser(description='Merge SELinux .te files.')
parser.add_argument('module_name', help='Name of the merged module.')
parser.add_argument('-d', '--dir', default='.', help='Directory to collect .te files for merging.')
args = parser.parse_args()
file_dir = args.dir

pattern_type = re.compile(r'type (.*?);')
pattern_class = re.compile(r'class (.*?) {(.*?)};')
pattern_class_single = re.compile(r'class (.*?) (.*?);')
pattern_allow = re.compile(r'allow (.*?) {(.*?)};')
pattern_allow_single = re.compile(r'allow (.*?) (.*?);')

merged_types = set()
merged_classes = defaultdict(set)
merged_allowances = defaultdict(set)

for filename in os.listdir(file_dir):
    if filename.endswith('.te'):
        with open(os.path.join(file_dir, filename), 'r') as file:
            file_data = file.read()

            # extract and merge types
            types = pattern_type.findall(file_data)
            merged_types.update(types)

            # extract and merge classes
            classes = pattern_class.findall(file_data)
            classes_single = pattern_class_single.findall(file_data)
            for class_name, permissions in classes + classes_single:
                merged_classes[class_name].update(permissions.split())

            # extract and merge allowances
            allowances = pattern_allow.findall(file_data)
            allowances_single = pattern_allow_single.findall(file_data)
            for allowance, permissions in allowances + allowances_single:
                merged_allowances[allowance].update(permissions.split())

with open(f'{args.module_name}.te', 'w') as file:
    file.write(f'module {args.module_name} 1.0;\n\nrequire {{\n')

    for type_name in sorted(merged_types):
        file.write(f'\ttype {type_name};\n')

    for class_name, permissions in sorted(merged_classes.items()):
        file.write(f'\tclass {class_name} {{ {" ".join(sorted(permissions))} }};\n')

    file.write('}\n')

    for allowance, permissions in sorted(merged_allowances.items()):
        file.write(f'allow {allowance} {{ {" ".join(sorted(permissions))} }};\n')
