import os
import argparse
import re

def parse_require_block(block):
    types, classes = set(), {}

    # Extract types
    type_matches = re.findall(r'type\s+([^;]+);', block, re.DOTALL)
    for t in type_matches:
        types.update(t.split())

    # Extract classes with braces
    class_brace_matches = re.findall(r'class\s+(\w+)\s*\{\s*([^}]+?)\s*\}\s*;', block, re.DOTALL)
    for cls, ops in class_brace_matches:
        if cls not in classes:
            classes[cls] = set()
        classes[cls].update(map(str.strip, ops.split()))

    # Extract classes without braces but with operations
    class_no_brace_ops_matches = re.findall(r'class\s+(\w+)\s+([\w_]+)\s*;', block, re.DOTALL)
    for cls, op in class_no_brace_ops_matches:
        if cls not in classes:
            classes[cls] = set()
        classes[cls].update([op.strip()])  # add operation

    # Extract classes without braces and without operations
    class_no_brace_no_ops_matches = re.findall(r'class\s+(\w+)\s*;', block, re.DOTALL)
    for cls in class_no_brace_no_ops_matches:
        if cls not in classes:
            classes[cls] = set()

    return list(types), classes

def find_matching_brace(content, start_index):
    brace_count = 0
    for i in range(start_index, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return i
    raise ValueError("No matching closing brace found from index {}".format(start_index))


def split_sections(content):
    require_start = content.find('require {')
    if require_start == -1:
        print(content);
        raise ValueError("No 'require {' block found in the content")

    require_end = find_matching_brace(content, require_start)
    require_section = content[require_start:require_end].strip()
    allow_section = content[require_end:].strip()

    return [require_section, allow_section]
    
def parse_allow_block(block):
    allow_rules = {}
    for line in block.split('\n'):
        if line.startswith("allow"):
            matches = re.findall(r'allow (\w+) (\w+:\w+) ({ ([^}]+) }|[\w_]+);', line)
            if matches:
                source, target, single_op, multi_ops = matches[0]
                
                ops = set(multi_ops.split()) if multi_ops else set([single_op])

                source_key = source + " " + target
                if source_key in allow_rules:
                    allow_rules[source_key].update(ops)
                else:
                    allow_rules[source_key] = ops
    return allow_rules

def merge_files(module_name, files):
    merged_types = set()
    merged_classes = {}
    merged_allows = {}

    for file_content in files:
        sections = split_sections(file_content)

        # Parsing the require block
        types, classes = parse_require_block(sections[0])
        merged_types.update(types)
        for cls, ops in classes.items():
            if cls not in merged_classes:
                merged_classes[cls] = set()
            merged_classes[cls].update(ops)

        # Parsing the allow block
        file_allow_rules = parse_allow_block(sections[1])
        
        for source_key, ops in file_allow_rules.items():
            if source_key not in merged_allows:
                merged_allows[source_key] = set()
            merged_allows[source_key].update(ops)
    # Create the merged .te content
    merged_content = []
    merged_content.append(f"module {module_name} 1.0;")
    merged_content.append("\nrequire {")
    for t in sorted(list(merged_types)):
        merged_content.append(f"    type {t};")
    for cls, ops in sorted(merged_classes.items()):
        ops = sorted(list(ops))
        if len(ops) == 1:
            merged_content.append(f"    class {cls} {ops[0]};")
        else:
            merged_content.append(f"    class {cls} {{ {' '.join(ops)} }};")
    merged_content.append("}\n")
    for ukey, ops in sorted(merged_allows.items()):
        ops = sorted(list(ops))
        merged_content.append(f"allow {ukey} {{ {' '.join(ops)} }};")

    return '\n'.join(merged_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Merge SELinux .te files.')
    parser.add_argument('module_name', type=str, help='Name of the merged module')
    parser.add_argument('--working_dir', type=str, default=os.getcwd(),
                        help='Working directory containing .te files to be merged. Defaults to the current directory.')

    args = parser.parse_args()

    te_files_content = []
    for filename in os.listdir(args.working_dir):
        if filename.endswith(".te"):
            with open(os.path.join(args.working_dir, filename), 'r') as file:
                print(f"Processing {filename}...")  # Add this line
                te_files_content.append(file.read())

            try:
                merged_content = merge_files(args.module_name, te_files_content)
            except Exception as e:
                print(f"An error occurred while processing {filename}: {e}")
                raise


    merged_content = merge_files(args.module_name, te_files_content)
    
    with open(f"{args.module_name}.te", 'w') as outfile:
        outfile.write(merged_content)

    print(f"Merged content written to {args.module_name}.te")
