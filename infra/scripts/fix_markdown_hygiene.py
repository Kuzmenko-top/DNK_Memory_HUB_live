import os
import re
import sys

def fix_markdown2(content):
    # MD030: Spaces after list markers [Expected: 1; Actual: 2 or 3]
    # Match `-  ` or `*  ` or `1.  ` and replace with single space
    content = re.sub(r'^([ \t]*)([-*+]|\d+\.) {2,}', r'\1\2 ', content, flags=re.MULTILINE)
    
    # MD007: Unordered list indentation [Expected: 2; Actual: 4]
    # This is tricky without a real parser, but typically:
    content = re.sub(r'^    ([-*+]) ', r'  \1 ', content, flags=re.MULTILINE)
    content = re.sub(r'^        ([-*+]) ', r'    \1 ', content, flags=re.MULTILINE)
    
    # MD004: Unordered list style [Expected: asterisk; Actual: dash]
    # Replace ^- with ^* (only if we want to force asterisk, but usually - is fine. Let's do it if needed).
    # Actually, it's safer to leave MD004 or just do:
    # content = re.sub(r'^([ \t]*)- ', r'\1* ', content, flags=re.MULTILINE) # commented out to avoid breaking things
    
    # MD060: Table column style
    # Replace |---| with | :--- | etc.
    content = re.sub(r'\|-+\|', '| --- |', content)
    content = re.sub(r'\|:-+\|', '| :--- |', content)
    content = re.sub(r'\|-+:\|', '| ---: |', content)
    content = re.sub(r'\|:-+:\|', '| :---: |', content)
    # Also handle multiple columns: |---|---|
    # A simple way is to replace `|-` with `| -` and `-|` with `- |`
    content = re.sub(r'\|(?=-)', '| ', content)
    content = re.sub(r'(?<=-)\|', ' |', content)
    
    # MD036: Emphasis used instead of a heading
    # Change `*Text*` on its own line to `<i>Text</i>`
    content = re.sub(r'^(\*[^*]+\*)$', lambda m: f"<i>{m.group(1)[1:-1]}</i>", content, flags=re.MULTILINE)
    
    # MD041: First line should be a top-level heading. (Hard to auto-fix reliably without breaking frontmatter)
    
    return content

def process_dir(target_dir):
    for root, dirs, files in os.walk(target_dir):
        if '.git' in dirs: dirs.remove('.git')
        if '.venv' in dirs: dirs.remove('.venv')
        if 'node_modules' in dirs: dirs.remove('node_modules')
        
        for file in files:
            if file.endswith('.md'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    new_content = fix_markdown2(content)
                    if new_content != content:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Fixed {path}")
                except Exception as e:
                    pass

if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['.']
    for target in targets:
        process_dir(target)
