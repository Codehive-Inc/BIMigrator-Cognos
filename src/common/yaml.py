import re


def parse_yaml(yaml_string):
    """
    Parses a simple YAML string and returns a dictionary.
    Supports basic key-value pairs and nested dictionaries.
    """
    lines = yaml_string.strip().split('\n')
    data = {}
    stack = [data]
    indent_level = [0]

    for line in lines:
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue
        match = re.match(r'(\s*)(.+?):\s*(.*)', line)
        if match:
            indent, key, value = match.groups()
            level = len(indent)
            key = key.strip()
            value = value.strip()

            while level < indent_level[-1]:
                stack.pop()
                indent_level.pop()

            if level > indent_level[-1]:
                new_dict = {}
                stack[-1][key] = new_dict
                stack.append(new_dict)
                indent_level.append(level)

            if value:
                stack[-1][key] = value
            else:
                stack[-1][key] = {}
                stack.append(stack[-1][key])
                indent_level.append(level + 2)
    return data
