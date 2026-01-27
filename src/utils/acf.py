"""
Modernized ACF Parser (Steam KeyValues Text Format)
"""
__all__ = ('load', 'loads', 'dump', 'dumps')

SECTION_START = '{'
SECTION_END = '}'

def loads(data: str, wrapper=dict):
    if not isinstance(data, str):
        raise TypeError(f'Can only load str, got {type(data).__name__}')

    parsed = wrapper()
    current_section = parsed
    sections = []
    lines = (line.strip() for line in data.splitlines() if line.strip())

    for line in lines:
        if line == SECTION_START:
            current_section = _prepare_subsection(parsed, sections, wrapper)
            continue
        if line == SECTION_END:
            if sections: sections.pop()
            continue

        try:
            # Try to split key-value
            parts = line.split(None, 1)
            if len(parts) == 2:
                key = parts[0].strip('"')
                value = parts[1].strip('"')
                current_section[key] = value
            else:
                # It's a new section
                sections.append(line.strip('"'))
        except ValueError:
            continue
    return parsed

def load(fp, wrapper=dict):
    return loads(fp.read(), wrapper=wrapper)

def dumps(obj: dict, level: int = 0) -> str:
    lines = []
    indent = '\t' * level
    for key, value in obj.items():
        if isinstance(value, dict):
            lines.append(f'{indent}"{key}"\n{indent}{{')
            lines.append(dumps(value, level + 1).rstrip())
            lines.append(f'{indent}}}')
        else:
            lines.append(f'{indent}"{key}"\t\t"{value}"')
    return '\n'.join(lines) + '\n'

def dump(obj: dict, fp):
    fp.write(dumps(obj))

def _prepare_subsection(data, sections, wrapper):
    current = data
    for section in sections:
        if section not in current:
            current[section] = wrapper()
        current = current[section]
    return current